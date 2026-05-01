from flask import Flask, request, jsonify, send_from_directory
from groq import Groq
from dotenv import load_dotenv
import os
import json
import datetime
import uuid

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

HISTORIAL_FILE = "historial.json"

def read_historial():
    if not os.path.exists(HISTORIAL_FILE):
        return []
    try:
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_historial(data):
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/informe", methods=["POST"])
def informe():
    data = request.get_json()
    notas = data.get("notas", "").strip()
    nombre = data.get("nombre", "No especificado")
    edad = data.get("edad", "No especificada")
    rut = data.get("rut", "No especificado")

    if not notas:
        return jsonify({"error": "Las notas no pueden estar vacias."}), 400

    prompt = (
        "Eres un medico clinico experto redactando un informe clinico formal. "
        "A partir de las notas de la consulta, genera un informe completo con el historial del paciente. "
        "Devuelve UNICAMENTE un objeto JSON valido, sin texto adicional, sin markdown, sin bloques de codigo. Solo el JSON puro.\n\n"
        f"Datos del paciente:\n- Nombre: {nombre}\n- Edad: {edad}\n- RUT: {rut}\n\n"
        f"Notas de la consulta:\n{notas}\n\n"
        "Devuelve exactamente este JSON con los campos completados en espanol:\n"
        "{\n"
        '  "motivo_consulta": "razon principal por la que el paciente asiste a la consulta, en 1-2 oraciones",\n'
        '  "historia_enfermedad": "descripcion detallada y cronologica de la enfermedad actual, incluyendo evolucion, duracion y contexto relevante",\n'
        '  "sintomas": ["sintoma especifico 1", "sintoma especifico 2"],\n'
        '  "antecedentes": ["antecedente medico, quirurgico, familiar o de habitos relevante"],\n'
        '  "temas_a_tratar": ["tema o problema a abordar en la consulta o seguimiento"],\n'
        '  "diagnostico": ["diagnostico confirmado o sospecha diagnostica"],\n'
        '  "medicamentos": ["medicamento con dosis si esta disponible"],\n'
        '  "plan": "plan de seguimiento detallado: examenes solicitados, interconsultas, indicaciones, proxima cita"\n'
        "}\n\n"
        "Si algun campo no aplica o no hay informacion suficiente, usa un array vacio [] o una cadena vacia \"\"."
    )

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        text = completion.choices[0].message.content.strip()
        parsed = json.loads(text)
        return jsonify(parsed)

    except Exception as e:
        error_str = str(e)
        print(f"Error Groq: {error_str}")
        if "429" in error_str:
            return jsonify({"error": "Limite de requests alcanzado. Espera un momento e intenta de nuevo."}), 429
        if "401" in error_str:
            return jsonify({"error": "API key de Groq invalida. Verifica tu archivo .env"}), 401
        return jsonify({"error": "Error al conectarse con la IA. Intenta de nuevo."}), 500

@app.route("/api/pacientes", methods=["GET"])
def get_pacientes():
    return jsonify(read_historial())

@app.route("/api/pacientes", methods=["POST"])
def save_paciente():
    data = request.get_json()
    historial = read_historial()
    
    nuevo_paciente = {
        "id": str(uuid.uuid4()),
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nombre": data.get("nombre", "No especificado"),
        "rut": data.get("rut", "No especificado"),
        "edad": data.get("edad", ""),
        "notas": data.get("notas", ""),
        "informe": data.get("informe", {})
    }
    
    historial.insert(0, nuevo_paciente) # Guardar al inicio
    save_historial(historial)
    return jsonify({"status": "ok", "paciente": nuevo_paciente})

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("MedNotas corriendo en http://localhost:5000")
    app.run(debug=True, port=5000)
