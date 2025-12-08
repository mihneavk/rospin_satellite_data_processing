import subprocess
import os
import sys
import time
from pathlib import Path

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback pentru versiuni foarte vechi de Python, deși nu e cazul aici
        pass


PIPELINE = [
    # --- ETAPA 1: DRUMURI ---
    {
        "folder": "grafuri",
        "script": "descarcare.py",
        "desc": "1. [Drumuri] Descărcare date OSM (.graphml)"
    },
    {
        "folder": "grafuri",
        "script": "matrice.py", 
        "desc": "2. [Drumuri] Rasterizare (Generare .tif simplu)"
    },
    {
        "folder": "grafuri",
        "script": "proximitate.py",
        "desc": "3. [Drumuri] Calcul Distanță (Propagare)"
    },

    # --- ETAPA 2: CĂI FERATE ---
    {
        "folder": "grafuri_tren",
        "script": "descarcare.py",
        "desc": "4. [Tren] Descărcare și Rasterizare Șine"
    },
    # NOTĂ: Verifică dacă ai salvat scriptul de distanță pentru tren ca 'propagare.py'
    # Dacă are alt nume (ex: pasul8...), modifică aici!
    {
        "folder": "grafuri_tren",
        "script": "matrice.py", 
        "desc": "5. [Tren] Calcul Distanță (Propagare)"
    },

    # --- ETAPA 3: HĂRȚI SATELITARE ---
    {
        "folder": "harti",
        "script": "full_generator_harta.py",
        "desc": "6. [Satelit] Download, Aliniere și Mascare"
    },
    {
        "folder": "harti",
        "script": "propagare.py",
        "desc": "7. [Satelit] Generare Hărți Distanță (Apă, Pădure, Urban)"
    },

    # --- ETAPA 4: ASAMBLARE FINALĂ (ROOT) ---
    # "." înseamnă folderul curent
    {
        "folder": ".",
        "script": "harta_mare.py",
        "desc": "8. [Master] Unificare Straturi (Data Cube BigTIFF)"
    },
    {
        "folder": ".",
        "script": "construibilitate.py",
        "desc": "9. [Master] Calcul Mască Construibil (Banda 6)"
    },
    {
        "folder": ".",
        "script": "scor_final.py",
        "desc": "10. [Final] Calcul SCOR TACTIC (0-45 puncte)"
    }
]

def run_step(step_info):
    folder = step_info["folder"]
    script = step_info["script"]
    desc = step_info["desc"]

    print(f"\n{'='*60}")
    print(f"RULEZ: {desc}")
    print(f"📂 Folder: {folder} | 📜 Script: {script}")
    print(f"{'='*60}")

    # Verificăm dacă scriptul există
    script_path = Path(folder) / script
    if not script_path.exists():
        print(f"❌ EROARE CRITICĂ: Nu găsesc scriptul: {script_path}")
        return False

    start_time = time.time()
    
    # Rulăm scriptul ca un sub-proces
    # cwd=folder asigură că scriptul "crede" că este rulat din folderul lui
    # (astfel își găsește fișierele relative corect)
    try:
        # sys.executable asigură că folosim același Python (din conda env)
        result = subprocess.run(
            [sys.executable, script], 
            cwd=folder, 
            check=True
        )
        
        duration = time.time() - start_time
        print(f"✅ SUCCES! Pas finalizat în {duration:.1f} secunde.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ EROARE la execuția scriptului '{script}'!")
        print(f"Cod eroare: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ EROARE NEAȘTEPTATĂ: {e}")
        return False

def main():
    print("🚀 PORNIRE PIPELINE GENERARE HARTĂ MILITARĂ")
    print(f"Total pași: {len(PIPELINE)}")
    
    total_start = time.time()
    
    for i, step in enumerate(PIPELINE, 1):
        print(f"\n--- Pasul {i}/{len(PIPELINE)} ---")
        success = run_step(step)
        
        if not success:
            print("\n🛑 OPRIRE DE URGENȚĂ: Pipeline-ul s-a oprit din cauza unei erori.")
            print("Rezolvă eroarea de mai sus și rulează din nou.")
            exit(1) # Ieșim cu cod de eroare

    total_duration = time.time() - total_start
    print(f"\n{'#'*60}")
    print(f"🎉 VICTORIE! TOATE ETAPELE COMPLETATE CU SUCCES!")
    print(f"⏱️ Timp total: {total_duration/60:.1f} minute")
    print(f"📁 Rezultat final: MATRICE_SCOR_FINAL.tif")
    print(f"{'#'*60}")

if __name__ == "__main__":
    main()