import os
import sys
import subprocess
import json
import osmnx as ox
from flask import Flask, request, jsonify, Response, send_file

app = Flask(__name__)

# --- CONFIGURARE DINAMICĂ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable 

SCRIPT_ANALIZA = "algoritm1_tif.py"
SCRIPT_UPDATE = "update_pipeline.py"
SCRIPT_VIZUALIZARE = "export_zona.py"  

OUTPUT_JSON = "rezultate_baze_gps.json"
OUTPUT_PNG = "zona_selectata.png"     

JUDETE_TARGET = [
    {"county": "Suceava", "country": "Romania"},
    {"county": "Botoșani", "country": "Romania"},
    {"county": "Iași", "country": "Romania"},
    {"county": "Neamț", "country": "Romania"},
    {"county": "Bacău", "country": "Romania"},
    {"county": "Vaslui", "country": "Romania"}
]

def run_subprocess(command_list):
    try:
        print(f"Executing: {' '.join(command_list)}")
        result = subprocess.run(
            command_list,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding='utf-8', 
            errors='replace'
        )
        return result
    except Exception as e:
        print(f"Subprocess Error: {e}")
        return None

@app.route("/api/boundaries", methods=["GET"])
def api_boundaries():
    try:
        print("Fetching county boundaries...")
        gdf = ox.geocode_to_gdf(JUDETE_TARGET)
        geojson_str = gdf.to_json()
        return Response(geojson_str, mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- RUTA NOUĂ: VIZUALIZARE ZONĂ (Returnează PNG) ---
@app.route("/api/visualize", methods=["POST"])
def api_visualize():
    data = request.get_json()
    zone = data.get("zone")

    if not zone:
        return jsonify({"error": "No zone selected"}), 400

    # Pregătim coordonatele
    lat1 = str(zone['nw'][0])
    lon1 = str(zone['nw'][1])
    lat2 = str(zone['se'][0])
    lon2 = str(zone['se'][1])

    script_path = os.path.join(BASE_DIR, SCRIPT_VIZUALIZARE)

    # Rulăm scriptul: python export_zona.py lat1 lon1 lat2 lon2
    cmd = [PYTHON_EXE, script_path, lat1, lon1, lat2, lon2]
    result = run_subprocess(cmd)

    if not result or result.returncode != 0:
        err_msg = result.stderr if result else "Unknown execution error"
        print(f"Eroare Vizualizare: {err_msg}")
        return jsonify({"error": "Visualization failed", "details": err_msg}), 500

    # Returnăm imaginea generată direct către browser
    png_path = os.path.join(BASE_DIR, OUTPUT_PNG)
    if os.path.exists(png_path):
        return send_file(png_path, mimetype='image/png')
    else:
        return jsonify({"error": "Image not generated"}), 500

@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json()
    zone = data.get("zone")
    preferences = data.get("preferences", {})

    if not zone:
        return jsonify({"error": "No zone selected"}), 400

    lat1 = str(zone['nw'][0])
    lon1 = str(zone['nw'][1])
    lat2 = str(zone['se'][0])
    lon2 = str(zone['se'][1])
    
    size = str(preferences.get("size", 20)) 
    count = str(preferences.get("count", 4))

    script_path = os.path.join(BASE_DIR, SCRIPT_ANALIZA)

    cmd = [PYTHON_EXE, script_path, lat1, lon1, lat2, lon2, size, count]
    result = run_subprocess(cmd)

    if not result or result.returncode != 0:
        err_msg = result.stderr if result else "Unknown execution error"
        print(f"Eroare Script (STDERR): {err_msg}")
        return jsonify({"error": "Analysis failed", "details": err_msg}), 500

    json_path = os.path.join(BASE_DIR, OUTPUT_JSON)
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding='utf-8') as f:
                bases = json.load(f)
            return jsonify(bases)
        except Exception as e:
            return jsonify({"error": f"Corrupt JSON output: {str(e)}"}), 500
    else:
        return jsonify([])

@app.route("/api/update", methods=["POST"])
def api_update():
    print("Starting Pipeline Update...")
    script_path = os.path.join(BASE_DIR, SCRIPT_UPDATE)
    cmd = [PYTHON_EXE, script_path]
    result = run_subprocess(cmd)

    if result and result.returncode == 0:
        return jsonify({
            "status": "success", 
            "message": "Toate hărțile au fost actualizate și recalculate.",
            "logs": result.stdout[-500:]
        })
    else:
        err = result.stderr if result else "Script not found"
        return jsonify({"status": "error", "message": err}), 500

@app.route("/")
def index():
    from flask import send_from_directory
    return send_from_directory(BASE_DIR, 'versiune1.html')

if __name__ == "__main__":
    app.run(debug=True, port=5000)