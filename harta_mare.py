import rasterio
import numpy as np
from pathlib import Path
import os
import sys



if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# --- CONFIGURARE ---
MAPS_CONFIG = [
    {"filename": "matrice_distanta_drum.tif",   "name": "dist_drum",   "desc": "Distanța Rutieră"},
    {"filename": "matrice_distanta_rail.tif",   "name": "dist_rail",   "desc": "Distanța Feroviară"},
    {"filename": "matrice_distanta_padure.tif", "name": "dist_padure", "desc": "Distanța Pădure"},
    {"filename": "matrice_distanta_apa.tif",    "name": "dist_apa",    "desc": "Distanța Apă"},
    {"filename": "matrice_distanta_urban.tif",  "name": "dist_urban",  "desc": "Distanța Urban"},
    {"filename": "matrice_relief_10m.tif",      "name": "elevatie",    "desc": "Altitudine (DEM)"}
]

OUTPUT_FILE = "MASTER_DATASET_NORD_EST.tif"

def cauta_fisier(nume_fisier):
    """Caută fișierul recursiv în folderul curent și vecini."""
    p = Path(nume_fisier)
    if p.exists(): return p
    # Căutăm în subfoldere și vecini
    locations = [Path("."), Path("..")]
    for loc in locations:
        for f in loc.rglob(nume_fisier):
            return f
    return None

def stack_rasters():
    print("--- 1. Căutăm hărțile ---")
    valid_maps = []
    
    for m in MAPS_CONFIG:
        fname = m["filename"]
        gasit = cauta_fisier(fname)
        if gasit:
            print(f"  ✅ Găsit: {m['name']}")
            m["full_path"] = gasit
            valid_maps.append(m)
        else:
            print(f"  ⚠️ LIPSĂ: {fname} (Va lipsi din analiza finală!)")
            
    if not valid_maps:
        print("EROARE: Nu am găsit niciun fișier.")
        return

    template_path = valid_maps[0]["full_path"]
    
    with rasterio.open(template_path) as src0:
        meta = src0.meta.copy()
        
    # --- MODIFICAREA CRITICĂ PENTRU FIȘIERE MARI ---
    meta.update(
        count=len(valid_maps), 
        dtype='float32', 
        compress='lzw',
        BIGTIFF='YES',     # <--- Aici este soluția! Permite fișiere > 4GB
        tiled=True         # Optimizează citirea pe bucăți
    )

    print(f"\n--- 2. Creăm Master Dataset BigTIFF ({len(valid_maps)} straturi) ---")
    
    with rasterio.open(OUTPUT_FILE, 'w', **meta) as dst:
        for idx, layer_info in enumerate(valid_maps, start=1):
            print(f"  -> Adăugăm Banda {idx}: {layer_info['name']}...")
            
            with rasterio.open(layer_info["full_path"]) as src:
                # Citim datele și le convertim la float32
                data = src.read(1).astype('float32')
                dst.write(data, idx)
                dst.set_band_description(idx, layer_info["name"])
    
    print(f"\n✅ SUCCES! '{OUTPUT_FILE}' (BigTIFF) a fost creat.")

def query_pixel(row, col):
    if not Path(OUTPUT_FILE).exists(): return None
    
    rezultat = {}
    with rasterio.open(OUTPUT_FILE) as src:
        # Verificăm limitele
        if row >= src.height or col >= src.width:
            return "Out of bounds"

        window = rasterio.windows.Window(col, row, 1, 1)
        values = src.read(window=window)
        
        for i, val in enumerate(values):
            band_name = src.descriptions[i] 
            rezultat[band_name] = float(val[0][0])
            
    return rezultat

if __name__ == "__main__":
    stack_rasters()
    
    if Path(OUTPUT_FILE).exists():
        print("\n--- TEST FINAL: Interogare Pixel ---")
        # Testăm un pixel valid
        data = query_pixel(12000, 12000)
        import pprint
        pprint.pprint(data)