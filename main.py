# ============================================================================
# 🌹 HIDROCONTROL - Servidor Flask para Render.com
# ============================================================================
# Propósito: Backend API para controlar sistema de riego con 15 válvulas
# Tecnologías: Flask (Python), CORS, JSON API, Persistencia en archivo
# Comunicación: HTTPS con frontend web y dispositivo ESP32
# Estructura: 3 bloques (block1, block2, block3) × 5 válvulas cada uno
# ============================================================================

# Importación de módulos necesarios para el funcionamiento del servidor
from flask import Flask, request, jsonify, render_template  # ✅ render_template incluido
from flask_cors import CORS  # Permite que el navegador web haga peticiones a esta API desde otro dominio
from datetime import datetime, timezone  # Para manejar fechas/horas con precisión y zona horaria UTC
import json  # Para guardar/cargar estados en archivo JSON (persistencia)
import os  # Para acceder a variables de entorno del sistema (como el puerto que asigna Render)

# ============================================================================
# 🚀 INICIALIZACIÓN DE LA APLICACIÓN FLASK
# ============================================================================
app = Flask(__name__)  # Crea la instancia principal de la aplicación Flask
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
    if os.path.exists(ARCHIVO_ESTADOS):  # Si el archivo ya existe
        try:
            with open(ARCHIVO_ESTADOS, 'r', encoding='utf-8') as f:  # Abrir para lectura
                return json.load(f)  # Parsear JSON y devolver diccionario
        except Exception as e:
            print(f"⚠️ Error cargando estados: {e}")  # Log de advertencia
            # Si hay error, continuar con valores por defecto
    
    # Estado inicial por defecto (3 bloques × 5 válvulas)
    estados_defecto = {  # ✅ Verificar: debe ser 'defecto' no 'defacto'
        "block1": {
            str(v): {"estado": "off", "programacion": None}  # Válvulas 1-5 apagadas, sin programación
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
    guardar_estados(estados_defecto)  # Guardar archivo inicial
    return estados_defecto  # ✅ Debe coincidir con el nombre de la variable

def guardar_estados(estados):
    """
    Guarda los estados en el archivo JSON para persistencia.
    Retorna True si éxito, False si error.
    """
    try:
        with open(ARCHIVO_ESTADOS, 'w', encoding='utf-8') as f:  # Abrir para escritura
            json.dump(estados, f, indent=2, ensure_ascii=False)  # Guardar con formato legible
        return True
    except Exception as e:
        print(f"❌ Error guardando estados: {e}")  # Log de error
        return False

# ============================================================================
# 🧠 MEMORIA GLOBAL DEL ESTADO - Se carga desde archivo al iniciar
# ============================================================================
# ✅ Con persistencia: los estados sobreviven a reinicios del servidor
estados_globales = cargar_estados()  # Cargar estados al iniciar la aplicación

# ============================================================================
# 🌐 RUTAS DE LA APLICACIÓN (ENDPOINTS DE LA API)
# ============================================================================

# -----------------------------------------------------------------------------
# 🏠 RUTA RAÍZ: Servir la Página Web HTML
# -----------------------------------------------------------------------------
@app.route('/', methods=['GET'])
def index():
    """
    Sirve la interfaz web HTML en lugar de JSON.
    Flask busca automáticamente en la carpeta 'templates/'
    """
    return render_template('index.html')

# -----------------------------------------------------------------------------
# 🕐 RUTA: Obtener Hora del Servidor (Para diagnóstico de zona horaria)
# -----------------------------------------------------------------------------
@app.route('/api/time', methods=['GET'])
def get_server_time():
    """
    Devuelve la hora actual del servidor en UTC.
    Útil para que el frontend ajuste programaciones según zona horaria local.
    """
    now_utc = datetime.now(timezone.utc)  # Hora actual en UTC
    return jsonify({
        "utc": now_utc.isoformat(),  # Timestamp completo ISO 8601
        "utc_time": now_utc.strftime("%H:%M:%S"),  # Solo hora legible "HH:MM:SS"
        "note": "Render usa UTC. Tu frontend debe ajustar según zona horaria local del usuario."
    }), 200

# -----------------------------------------------------------------------------
# 📥 GET: Consultar estado de un bloque completo
# -----------------------------------------------------------------------------
@app.route('/api/bloque/<block_id>', methods=['GET'])
def get_bloque(block_id):
    """
    Devuelve el estado de las 5 válvulas de un bloque específico.
    block_id: 'block1', 'block2' o 'block3'
    """
    if block_id not in estados_globales:  # Validar que el bloque existe
        return jsonify({
            "error": f"Bloque '{block_id}' no existe",
            "bloques_disponibles": list(estados_globales.keys())
        }), 404  # Código 404: No encontrado
    
    # Devolver estado del bloque con timestamp para sincronización
    return jsonify({
        "block_id": block_id,
        "timestamp": datetime.utcnow().isoformat(),
        "valvulas": estados_globales[block_id]  # Diccionario con válvulas 1-5
    }), 200

# -----------------------------------------------------------------------------
# 📥 GET: Consultar estado de una válvula específica
# -----------------------------------------------------------------------------
@app.route('/api/valvula/<block_id>/<int:num>', methods=['GET'])
def get_valvula(block_id, num):
    """
    Devuelve el estado de una válvula específica.
    num: número de válvula (1-5)
    """
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
    """
    Cambia el estado de una válvula específica.
    Estados válidos: 'on' (encendida), 'off' (apagada), 'auto' (programada)
    """
    # Validar que el bloque y válvula existen
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    try:
        datos = request.get_json()  # Parsear JSON recibido
        if not datos:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
        
        nuevo_estado = datos.get('estado', '').lower()  # Obtener y normalizar estado
        
        # Validar que el estado sea válido
        if nuevo_estado not in ['on', 'off', 'auto']:
            return jsonify({
                "error": "Estado inválido",
                "estados_validos": ["on", "off", "auto"]
            }), 400
        
        # ✅ Actualizar estado en memoria global
        estados_globales[block_id][str(num)]["estado"] = nuevo_estado
        estados_globales[block_id][str(num)]["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()
        
        # ✅ GUARDAR EN ARCHIVO (Persistencia real - los estados NO se pierden)
        guardar_estados(estados_globales)
        
        # 📡 Aquí iría la lógica para enviar orden al ESP32 (si está conectado)
        # enviar_orden_esp32(block_id, num, nuevo_estado)
        
        print(f"✅ Comando: {block_id} válvula {num} → {nuevo_estado.upper()}")  # Log en consola
        return jsonify({
            "mensaje": f"Válvula {num} del {block_id} cambiada a {nuevo_estado}",
            "block_id": block_id,
            "num": num,
            "estado": nuevo_estado,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error en set_valvula: {e}")  # Log de error
        return jsonify({"error": str(e)}), 500  # Código 500: Error interno del servidor

# -----------------------------------------------------------------------------
# 📤 POST: Guardar programación automática de una válvula
# -----------------------------------------------------------------------------
@app.route('/api/valvula/<block_id>/<int:num>/programacion', methods=['POST'])
def set_programacion(block_id, num):
    """
    Guarda la programación (horarios ON/OFF) de una válvula específica.
    Formato de hora: "HH:MM" en hora local del usuario.
    """
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
        
        # Validar que se proporcionaron ambas horas
        if not hora_on or not hora_off:
            return jsonify({"error": "Debe proporcionar horas 'on' y 'off'"}), 400
        
        # ✅ Actualizar programación en memoria
        estados_globales[block_id][str(num)]["programacion"] = {
            "on": hora_on,
            "off": hora_off
        }
        # Cambiar estado a 'auto' para indicar que está programada
        estados_globales[block_id][str(num)]["estado"] = "auto"
        estados_globales[block_id][str(num)]["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()
        
        # ✅ GUARDAR EN ARCHIVO (Persistencia)
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
    """
    Elimina la programación automática de una válvula específica.
    La válvula vuelve a estado 'off' y sin horarios programados.
    """
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    try:
        # ✅ Limpiar programación en memoria
        estados_globales[block_id][str(num)]["programacion"] = None
        estados_globales[block_id][str(num)]["estado"] = "off"  # Volver a apagada
        estados_globales[block_id][str(num)]["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()
        
        # ✅ GUARDAR EN ARCHIVO (Persistencia)
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
# 🏓 Health Check (para verificar que el servidor está activo)
# -----------------------------------------------------------------------------
@app.route('/api/health', methods=['GET'])
def health():
    """
    Verifica el estado del servidor y devuelve resumen.
    Útil para monitoreo y diagnóstico.
    """
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
    # Obtener puerto desde variable de entorno (Render asigna puerto dinámico)
    # Si no existe PORT, usar 5000 como fallback para desarrollo local
    port = int(os.environ.get('PORT', 5000))
    
    # Iniciar servidor Flask en modo desarrollo
    # host='0.0.0.0' permite conexiones desde cualquier IP (requerido por Render)
    # debug=False en producción (Render lo maneja)
    print(f"🚀 Iniciando HIDROCONTROL API en puerto {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
