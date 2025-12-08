import os
import sys
import subprocess
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURARE DINAMICĂ (UNIVERSALĂ) ---
# Detectăm automat unde ne aflăm și ce Python folosim
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable  # Folosește Python-ul care rulează acest script (cel din mediu)

# Numele scripturilor (trebuie să fie în același folder)
SCRIPT_ANALIZA = "algoritm1_tif.py"
SCRIPT_UPDATE = "update_pipeline.py"
OUTPUT_JSON = "rezultate_baze_gps.json"

def run_subprocess(command_list):
    """Funcție helper pentru a rula comenzi și a prinde erorile."""
    try:
        print(f"Executing: {' '.join(command_list)}")
        
        # --- FIX PENTRU WINDOWS ENCODING ---
        # Adăugăm encoding='utf-8' și errors='replace' pentru a evita crash-ul la diacritice
        result = subprocess.run(
            command_list,
            cwd=BASE_DIR,        # Executăm în folderul proiectului
            capture_output=True, # Prindem output-ul
            text=True,           # Output-ul este text, nu bytes
            encoding='utf-8',    # <--- ESENȚIAL: Citim ca UTF-8
            errors='replace'     # <--- SAFETY: Dacă apare un caracter ciudat, îl înlocuim cu ?, nu crăpăm
        )
        return result
    except Exception as e:
        print(f"Subprocess Error: {e}")
        return None

# --- RUTA 1: LANSARE ANALIZĂ (RUN) ---
@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json()
    zone = data.get("zone")
    preferences = data.get("preferences", {})

    if not zone:
        return jsonify({"error": "No zone selected"}), 400

    # 1. Pregătim argumentele pentru script
    # Leaflet trimite: nw: [lat, lng], se: [lat, lng]
    lat1 = str(zone['nw'][0])
    lon1 = str(zone['nw'][1])
    lat2 = str(zone['se'][0])
    lon2 = str(zone['se'][1])
    
    size = str(preferences.get("size", 20)) 
    count = str(preferences.get("count", 4))

    script_path = os.path.join(BASE_DIR, SCRIPT_ANALIZA)

    # 2. Rulăm algoritm1_tif.py
    cmd = [PYTHON_EXE, script_path, lat1, lon1, lat2, lon2, size, count]
    result = run_subprocess(cmd)

    if not result or result.returncode != 0:
        # Dacă crapă, afișăm eroarea din script (stderr)
        err_msg = result.stderr if result else "Unknown execution error"
        print(f"Eroare Script (STDERR): {err_msg}")
        return jsonify({"error": "Analysis failed", "details": err_msg}), 500

    # 3. Citim rezultatul din JSON-ul generat de script
    json_path = os.path.join(BASE_DIR, OUTPUT_JSON)
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding='utf-8') as f: # Citim JSON tot cu utf-8
                bases = json.load(f)
            return jsonify(bases)
        except Exception as e:
            return jsonify({"error": f"Corrupt JSON output: {str(e)}"}), 500
    else:
        # Dacă scriptul a rulat dar nu a generat JSON (poate zona e goală)
        return jsonify([])

# --- RUTA 2: ACTUALIZARE DATE (UPDATE) ---
@app.route("/api/update", methods=["POST"])
def api_update():
    print("Starting Pipeline Update...")
    
    script_path = os.path.join(BASE_DIR, SCRIPT_UPDATE)
    
    # Rulăm update_pipeline.py
    cmd = [PYTHON_EXE, script_path]
    result = run_subprocess(cmd)

    if result and result.returncode == 0:
        return jsonify({
            "status": "success", 
            "message": "Toate hărțile au fost actualizate și recalculate.",
            "logs": result.stdout[-500:] # Trimitem ultimele loguri
        })
    else:
        err = result.stderr if result else "Script not found"
        return jsonify({"status": "error", "message": err}), 500

# --- RUTA 3: SERVIRE HTML ---
@app.route("/")
def index():
    # Trimitem interfața direct
    from flask import send_from_directory
    return send_from_directory(BASE_DIR, 'versiune1.html')

if __name__ == "__main__":
    app.run(debug=True, port=5000)