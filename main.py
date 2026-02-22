# main.py - Servidor Flask para Render (CON CORS y hora UTC)
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime, timezone
import os

app = Flask(__name__)
CORS(app)  # Permite peticiones desde cualquier origen

# Memoria temporal del estado del LED
estado_led = {
    "led": "off",
    "ultima_actualizacion": None,
    "programacion": None
}

# Página principal
@app.route('/')
def home():
    return render_template('index.html')

# API: ESP32 consulta el estado (GET)
@app.route('/api/estado', methods=['GET'])
def get_estado():
    return jsonify(estado_led), 200

# API: Web envía comandos (POST)
@app.route('/api/estado', methods=['POST'])
def set_estado():
    try:
        datos = request.get_json()
        nuevo_estado = datos.get('led', '').lower()
        
        if nuevo_estado in ['on', 'off']:
            estado_led['led'] = nuevo_estado
            estado_led['ultima_actualizacion'] = datetime.now(timezone.utc).isoformat()
            print(f"✅ Comando recibido: LED {nuevo_estado.upper()}")
            return jsonify({"status": "ok", "led": nuevo_estado}), 200
        else:
            return jsonify({"error": "Usa 'on' o 'off'"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API: Programar horarios (POST)
@app.route('/api/programar', methods=['POST'])
def programar():
    try:
        datos = request.get_json()
        estado_led['programacion'] = {
            "on": datos.get('on'),
            "off": datos.get('off')
        }
        estado_led['ultima_actualizacion'] = datetime.now(timezone.utc).isoformat()
        print(f"⏰ Programación: ON {datos.get('on')} - OFF {datos.get('off')}")
        return jsonify({"status": "ok", "programacion": estado_led['programacion']}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# API: Eliminar programación (DELETE)
@app.route('/api/programar', methods=['DELETE'])
def eliminar_programacion():
    """Elimina la programación automática"""
    estado_led['programacion'] = None
    estado_led['ultima_actualizacion'] = datetime.now(timezone.utc).isoformat()
    print("🗑️ Programación eliminada")
    return jsonify({"status": "ok", "mensaje": "Programación eliminada"}), 200

# API: Obtener hora del servidor (para diagnóstico de timezone)
@app.route('/api/time', methods=['GET'])
def get_server_time():
    now_utc = datetime.now(timezone.utc)
    return jsonify({
        "utc": now_utc.isoformat(),
        "utc_time": now_utc.strftime("%H:%M:%S"),
        "note": "Render usa UTC. Ajusta tu programación según tu zona horaria."
    }), 200

# Iniciar servidor
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
