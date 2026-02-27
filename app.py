# app.py - Backend Flask para HIDROCONTROL (Latina Farms 3)
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)  # ✅ Permite peticiones desde tu frontend

# ============================================
# 📁 CONFIGURACIÓN DE PERSISTENCIA
# ============================================
ARCHIVO_ESTADOS = 'estados.json'

# ============================================
# 💾 FUNCIONES DE GUARDADO/CARGA
# ============================================
def cargar_estados():
    """Carga los estados desde el archivo JSON o crea valores por defecto"""
    if os.path.exists(ARCHIVO_ESTADOS):
        try:
            with open(ARCHIVO_ESTADOS, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
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
    """Guarda los estados en el archivo JSON"""
    try:
        with open(ARCHIVO_ESTADOS, 'w', encoding='utf-8') as f:
            json.dump(estados, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error guardando estados: {e}")
        return False

# Cargar estados al iniciar la aplicación
estados_globales = cargar_estados()

# ============================================
# 🏓 ENDPOINTS DE LA API
# ============================================

# 📥 GET: Consultar estado de un bloque completo
@app.route('/api/bloque/<block_id>', methods=['GET'])
def get_bloque(block_id):
    """Devuelve el estado de las 5 válvulas de un bloque"""
    if block_id not in estados_globales:
        return jsonify({
            "error": f"Bloque '{block_id}' no existe",
            "bloques_disponibles": list(estados_globales.keys())
        }), 404
    
    return jsonify({
        "block_id": block_id,
        "timestamp": datetime.utcnow().isoformat(),
        "valvulas": estados_globales[block_id]
    })

# 📥 GET: Consultar estado de una válvula específica
@app.route('/api/valvula/<block_id>/<int:num>', methods=['GET'])
def get_valvula(block_id, num):
    """Devuelve el estado de una válvula específica"""
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    return jsonify({
        "block_id": block_id,
        "num": num,
        "estado": estados_globales[block_id][str(num)]["estado"],
        "programacion": estados_globales[block_id][str(num)]["programacion"],
        "timestamp": datetime.utcnow().isoformat()
    })

# 📤 POST: Cambiar estado de una válvula (ENCENDER/APAGAR)
@app.route('/api/valvula/<block_id>/<int:num>', methods=['POST'])
def set_valvula(block_id, num):
    """Cambia el estado de una válvula específica"""
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    datos = request.get_json()
    if not datos:
        return jsonify({"error": "No se recibieron datos JSON"}), 400
    
    nuevo_estado = datos.get('estado')
    
    if nuevo_estado not in ['on', 'off', 'auto']:
        return jsonify({
            "error": "Estado inválido",
            "estados_validos": ["on", "off", "auto"]
        }), 400
    
    # ✅ Actualizar estado en memoria
    estados_globales[block_id][str(num)]["estado"] = nuevo_estado
    
    # ✅ GUARDAR EN ARCHIVO (Persistencia real)
    guardar_estados(estados_globales)
    
    # 📡 Aquí iría la lógica para enviar orden al ESP32
    # enviar_orden_esp32(block_id, num, nuevo_estado)
    
    return jsonify({
        "mensaje": f"Válvula {num} del {block_id} cambiada a {nuevo_estado}",
        "block_id": block_id,
        "num": num,
        "estado": nuevo_estado,
        "timestamp": datetime.utcnow().isoformat()
    })

# 📤 POST: Guardar programación de una válvula
@app.route('/api/valvula/<block_id>/<int:num>/programacion', methods=['POST'])
def set_programacion(block_id, num):
    """Guarda la programación (horarios ON/OFF) de una válvula"""
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    datos = request.get_json()
    if not datos:
        return jsonify({"error": "No se recibieron datos JSON"}), 400
    
    hora_on = datos.get('on')
    hora_off = datos.get('off')
    
    if not hora_on or not hora_off:
        return jsonify({"error": "Debe proporcionar horas 'on' y 'off'"}), 400
    
    # ✅ Actualizar programación
    estados_globales[block_id][str(num)]["programacion"] = {
        "on": hora_on,
        "off": hora_off
    }
    estados_globales[block_id][str(num)]["estado"] = "auto"
    
    # ✅ GUARDAR EN ARCHIVO
    guardar_estados(estados_globales)
    
    return jsonify({
        "mensaje": f"Programación actualizada para Válvula {num} del {block_id}",
        "block_id": block_id,
        "num": num,
        "programacion": estados_globales[block_id][str(num)]["programacion"],
        "timestamp": datetime.utcnow().isoformat()
    })

# ❌ DELETE: Eliminar programación de una válvula
@app.route('/api/valvula/<block_id>/<int:num>/programacion', methods=['DELETE'])
def delete_programacion(block_id, num):
    """Elimina la programación de una válvula"""
    if block_id not in estados_globales:
        return jsonify({"error": "Bloque no existe"}), 404
    if str(num) not in estados_globales[block_id]:
        return jsonify({"error": "Válvula no existe"}), 404
    
    # ✅ Limpiar programación
    estados_globales[block_id][str(num)]["programacion"] = None
    estados_globales[block_id][str(num)]["estado"] = "off"
    
    # ✅ GUARDAR EN ARCHIVO
    guardar_estados(estados_globales)
    
    return jsonify({
        "mensaje": f"Programación eliminada para Válvula {num} del {block_id}",
        "block_id": block_id,
        "num": num,
        "timestamp": datetime.utcnow().isoformat()
    })

# 🏓 Health Check (para verificar que el servidor está activo)
@app.route('/api/health', methods=['GET'])
def health():
    """Verifica el estado del servidor"""
    return jsonify({
        "status": "ok",
        "mensaje": "Servidor HIDROCONTROL activo",
        "timestamp": datetime.utcnow().isoformat(),
        "bloques": list(estados_globales.keys()),
        "total_valvulas": sum(len(b) for b in estados_globales.values())
    })

# 🏠 Ruta raíz (para verificar que la app carga)
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "mensaje": "🌹 Bienvenido a HIDROCONTROL API - Latina Farms 3",
        "endpoints": {
            "GET /api/health": "Verificar estado del servidor",
            "GET /api/bloque/<block_id>": "Obtener estado de un bloque",
            "GET /api/valvula/<block_id>/<num>": "Obtener estado de una válvula",
            "POST /api/valvula/<block_id>/<num>": "Cambiar estado de una válvula",
            "POST /api/valvula/<block_id>/<num>/programacion": "Guardar programación",
            "DELETE /api/valvula/<block_id>/<num>/programacion": "Eliminar programación"
        }
    })

# ============================================
# 🚀 EJECUCIÓN
# ============================================
if __name__ == '__main__':
    # Obtener puerto del entorno (para Render) o usar 5000 por defecto
    port = int(os.environ.get('PORT', 5000))
    # debug=False en producción (Render lo maneja)
    app.run(host='0.0.0.0', port=port, debug=False)

