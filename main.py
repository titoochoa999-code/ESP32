# ============================================================================
# 🌹 HIDROCONTROL - Servidor Flask para Render.com
# ============================================================================
# Propósito: Backend API para controlar sistema de riego con 15 válvulas
# Tecnologías: Flask (Python), CORS, JSON API, Persistencia en archivo
# Comunicación: HTTPS con frontend web y dispositivo ESP32
# Estructura: 3 bloques (block1, block2, block3) × 5 válvulas cada uno
# ============================================================================

# Importación de módulos necesarios para el funcionamiento del servidor
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timezone
import json
import os

# ============================================================================
# 🚀 INICIALIZACIÓN DE LA APLICACIÓN FLASK
# ============================================================================
app = Flask(__name__)
CORS(app)  # Habilita Cross-Origin Resource Sharing: permite fetch() desde tu frontend

# ============================================================================
# 📁 CONFIGURACIÓN DE PERSISTENCIA
# ============================================================================
ARCHIVO_ESTADOS = 'estados.json'  # Nombre del archivo para guardar estados permanentemente

# ============================================================================
# 💾 FUNCIONES DE GUARDADO/CARGA (Persistencia Real)
# ============================================================================
def cargar_estados():
    """
    Carga los estados desde el archivo JSON o crea valores por defecto.
    Esto asegura que los estados NO se pierdan al reiniciar el servidor.
    """
    if os.path.exists(ARCHIVO_ESTADOS):
        try:
            with open(ARCHIVO_ESTADOS, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error cargando estados: {e}")
    
    # Estado inicial por defecto (3 bloques × 5 válvulas)
    estados_defecto = {
        "block1": {
            str(v): {"estado": "off", "programacion": None}
            for v in range(1, 6)
        },
        "block2": {
            str(v): {"estado": "off", "programacion": None}
            for v in range(1, 6)
        },
        "block3": {
            str(v): {"estado": "off", "programacion": None}
            for v in range(1, 6)
        }
    }
    guardar_estados(estados_defecto)
    return estados_defecto

def guardar_estados(estados):
    """
    Guarda los estados en el archivo JSON para persistencia.
    Retorna True si éxito, False si error.
    """
    try:
        with open(ARCHIVO_ESTADOS, 'w', encoding='utf-8') as f:
            json.dump(estados, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error guardando estados: {e}")
        return False

# ============================================================================
# 🧠 MEMORIA GLOBAL DEL ESTADO - Se carga desde archivo al iniciar
# ============================================================================
estados_globales = cargar_estados()

# ============================================================================
# 🌐 RUTAS DE LA APLICACIÓN (ENDPOINTS DE LA API)
# ============================================================================

# -----------------------------------------------------------------------------
# 🏠 RUTA RAÍZ: Servir la Página Web HTML
# -----------------------------------------------------------------------------
@app.route('/', methods=['GET'])
def index():
    """Sirve la interfaz web HTML en lugar de JSON"""
    return render_template('index.html')

# -----------------------------------------------------------------------------
# 🕐 RUTA: Obtener Hora del Servidor
# -----------------------------------------------------------------------------
@app.route('/api/time', methods=['GET'])
def get_server_time():
    """Devuelve la hora actual del servidor en UTC"""
    now_utc = datetime.now(timezone.utc)
    return jsonify({
        "utc": now_utc.isoformat(),
        "utc_time": now_utc.strftime("%H:%M:%S"),
        "note": "Render usa UTC. Tu frontend debe ajustar según zona horaria local."
    }), 200

# -----------------------------------------------------------------------------
# 📥 GET: Consultar estado de un bloque completo
# -----------------------------------------------------------------------------
@app.route('/api/bloque/<block_id>', methods=['GET'])
def get_bloque(block_id):
    """Devuelve el estado de las 5 válvulas de un bloque específico"""
    if block_id not in estados_globales:
        return jsonify({
            "error": f"Bloque '{block_id}' no existe",
            "bloques_disponibles": list(estados_globales.keys())
        }), 404
    
    return jsonify({
        "block_id": block_id,
        "timestamp": datetime.utcnow().isoformat(),
        "valvulas": estados_globales[block_id]
    }), 200

# -----------------------------------------------------------------------------
# 📥 GET: Consultar estado de una válvula específica
# -----------------------------------------------------------------------------
@app.route('/api/valvula/<block_id>/<int:num>', methods=['GET'])
def get_valvula(block_id, num):
    """Devuelve el estado de una válvula específica"""
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    valvula = estados_globales[block_id][str(num)]
    return jsonify({
        "block_id": block_id,
        "num": num,
        "estado": valvula["estado"],
        "programacion": valvula["programacion"],
        "timestamp": datetime.utcnow().isoformat()
    }), 200

# -----------------------------------------------------------------------------
# 📤 POST: Cambiar estado de una válvula (ENCENDER/APAGAR)
# -----------------------------------------------------------------------------
@app.route('/api/valvula/<block_id>/<int:num>', methods=['POST'])
def set_valvula(block_id, num):
    """Cambia el estado de una válvula específica"""
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    try:
        datos = request.get_json()
        if not datos:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
        
        nuevo_estado = datos.get('estado', '').lower()
        
        if nuevo_estado not in ['on', 'off', 'auto']:
            return jsonify({
                "error": "Estado inválido",
                "estados_validos": ["on", "off", "auto"]
            }), 400
        
        # Actualizar estado en memoria global
        estados_globales[block_id][str(num)]["estado"] = nuevo_estado
        estados_globales[block_id][str(num)]["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()
        
        # GUARDAR EN ARCHIVO (Persistencia real)
        guardar_estados(estados_globales)
        
        print(f"✅ Comando: {block_id} válvula {num} → {nuevo_estado.upper()}")
        return jsonify({
            "mensaje": f"Válvula {num} del {block_id} cambiada a {nuevo_estado}",
            "block_id": block_id,
            "num": num,
            "estado": nuevo_estado,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error en set_valvula: {e}")
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# 📤 POST: Guardar programación automática de una válvula
# -----------------------------------------------------------------------------
@app.route('/api/valvula/<block_id>/<int:num>/programacion', methods=['POST'])
def set_programacion(block_id, num):
    """Guarda la programación (horarios ON/OFF) de una válvula específica"""
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    try:
        datos = request.get_json()
        if not datos:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
        
        hora_on = datos.get('on')
        hora_off = datos.get('off')
        
        if not hora_on or not hora_off:
            return jsonify({"error": "Debe proporcionar horas 'on' y 'off'"}), 400
        
        # Actualizar programación en memoria
        estados_globales[block_id][str(num)]["programacion"] = {
            "on": hora_on,
            "off": hora_off
        }
        estados_globales[block_id][str(num)]["estado"] = "auto"
        estados_globales[block_id][str(num)]["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()
        
        # GUARDAR EN ARCHIVO
        guardar_estados(estados_globales)
        
        print(f"⏰ Programación: {block_id} válvula {num} → ON {hora_on} / OFF {hora_off}")
        return jsonify({
            "mensaje": f"Programación actualizada para Válvula {num} del {block_id}",
            "block_id": block_id,
            "num": num,
            "programacion": estados_globales[block_id][str(num)]["programacion"],
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error en set_programacion: {e}")
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# ❌ DELETE: Eliminar programación de una válvula
# -----------------------------------------------------------------------------
@app.route('/api/valvula/<block_id>/<int:num>/programacion', methods=['DELETE'])
def delete_programacion(block_id, num):
    """Elimina la programación automática de una válvula específica"""
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    try:
        # Limpiar programación en memoria
        estados_globales[block_id][str(num)]["programacion"] = None
        estados_globales[block_id][str(num)]["estado"] = "off"
        estados_globales[block_id][str(num)]["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()
        
        # GUARDAR EN ARCHIVO
        guardar_estados(estados_globales)
        
        print(f"🗑️ Programación eliminada: {block_id} válvula {num}")
        return jsonify({
            "mensaje": f"Programación eliminada para Válvula {num} del {block_id}",
            "block_id": block_id,
            "num": num,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error en delete_programacion: {e}")
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# 📡 ENDPOINTS PARA COMUNICACIÓN CON ESP32
# -----------------------------------------------------------------------------

@app.route('/api/estado-esp32', methods=['GET'])
def get_estado_esp32():
    """
    Devuelve el estado de las 15 válvulas en formato plano para el ESP32.
    Formato: {"block1-1": "on", "block1-2": "off", ...}
    """
    valvulas_esp32 = {}
    
    for block_id in estados_globales:
        for num in estados_globales[block_id]:
            clave = f"{block_id}-{num}"
            valvulas_esp32[clave] = estados_globales[block_id][num]["estado"]
    
    return jsonify({
        "valvulas": valvulas_esp32,
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route('/api/estado-esp32', methods=['POST'])
def set_estado_esp32():
    """
    Recibe el estado actual físico del ESP32 (heartbeat).
    Útil para sincronización y monitoreo.
    """
    try:
        datos = request.get_json()
        valvulas_esp32 = datos.get('valvulas', {})
        
        for clave, estado in valvulas_esp32.items():
            partes = clave.split('-')
            if len(partes) == 2:
                block_id = partes[0]
                num = partes[1]
                
                if block_id in estados_globales and num in estados_globales[block_id]:
                    estados_globales[block_id][num]["estado"] = estado
        
        guardar_estados(estados_globales)
        
        return jsonify({
            "status": "ok",
            "mensaje": "Estado ESP32 recibido",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error en set_estado_esp32: {e}")
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# 🏓 Health Check (para verificar que el servidor está activo)
# -----------------------------------------------------------------------------
@app.route('/api/health', methods=['GET'])
def health():
    """Verifica el estado del servidor y devuelve resumen"""
    total_valvulas = sum(len(bloque) for bloque in estados_globales.values())
    return jsonify({
        "status": "ok",
        "mensaje": "🌹 Servidor HIDROCONTROL activo - Latina Farms 3",
        "timestamp": datetime.utcnow().isoformat(),
        "bloques_disponibles": list(estados_globales.keys()),
        "total_valvulas": total_valvulas
    }), 200

# ============================================================================
# 🚀 PUNTO DE ENTRADA - Ejecución del Servidor
# ============================================================================
if __name__ == '__main__':
    """
    Punto de entrada principal: se ejecuta solo si el archivo se corre directamente.
    En Render.com, esta sección se omite y se usa Gunicorn como servidor de producción.
    """
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando HIDROCONTROL API en puerto {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
