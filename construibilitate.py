import rasterio
import numpy as np
from scipy.ndimage import binary_erosion
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
INPUT_FILE = "MASTER_DATASET_NORD_EST.tif"
OUTPUT_FILE = "MASTER_DATASET_EXTENDED.tif"

# Parametrii Pădurii
DISTANTA_INTERIOR_PADURE = 50 # metri
PIXEL_SIZE = 10 # metri
ITERATII_EROZIUNE = DISTANTA_INTERIOR_PADURE // PIXEL_SIZE # 5 pixeli

def calculeaza_construibil():
    if not Path(INPUT_FILE).exists():
        print(f"EROARE: Nu găsesc '{INPUT_FILE}'.")
        return

    # Ștergem fișierul vechi de output dacă există
    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
        except PermissionError:
            print(f"EROARE: Nu pot șterge '{OUTPUT_FILE}'. Este deschis?")
            return

    with rasterio.open(INPUT_FILE) as src:
        # Copiem metadatele și adăugăm o bandă în plus
        profile = src.profile.copy()
        nr_benzi_originale = src.count
        
        profile.update(
            count=nr_benzi_originale + 1, # Adăugăm un strat
            BIGTIFF='YES',
            compress='lzw',
            tiled=True
        )
        
        # Identificăm indexul benzilor (bazat pe ordinea din scriptul anterior)
        # 1:Drum, 2:Rail, 3:Padure, 4:Apa, 5:Urban
        idx_drum = 1
        idx_rail = 2
        idx_padure = 3
        idx_apa = 4
        idx_urban = 5

        print("--- Pasul 1: Calculăm 'Pădurea Adâncă' (Global) ---")
        # Citim toată banda de pădure pentru a face eroziunea corect
        print("Citesc stratul de pădure...")
        banda_padure = src.read(idx_padure)
        
        # Masca Pădurii: Unde valoarea este -1 (Interior Pădure)
        mask_padure = (banda_padure == -1)
        
        print(f"Erodez pădurea cu {ITERATII_EROZIUNE} pixeli ({DISTANTA_INTERIOR_PADURE}m)...")
        # True unde ești adânc în pădure (neconstruibil)
        mask_padure_adanca = binary_erosion(mask_padure, iterations=ITERATII_EROZIUNE)
        
        del banda_padure 
        print("Calcul pădure finalizat.")

        print(f"\n--- Pasul 2: Generăm '{OUTPUT_FILE}' ---")
        
        with rasterio.open(OUTPUT_FILE, 'w', **profile) as dst:
            # Setăm descrierile benzilor
            dst.descriptions = src.descriptions + ("Construibil (Bool)",)
            
            # Definim indecșii pentru scrierea datelor originale (de la 1 la 5)
            indexes_original = list(range(1, nr_benzi_originale + 1))
            
            windows = [window for ij, window in dst.block_windows(1)]
            print(f"Procesez {len(windows)} blocuri de date...")
            
            # Încercăm să importăm tqdm, dacă nu, folosim iterator simplu
            try:
                from tqdm import tqdm
                iterator = tqdm(windows)
            except ImportError:
                iterator = windows

            for window in iterator:
                # 1. Citim datele originale
                data_block = src.read(window=window)
                
                # 2. Scriem datele originale în straturile 1-5
                # --- AICI ERA EROAREA: Specificăm indexes explicit ---
                dst.write(data_block, window=window, indexes=indexes_original)
                
                # 3. Calculăm Stratul CONSTRUIBIL
                b_drum = data_block[idx_drum - 1]
                b_rail = data_block[idx_rail - 1]
                b_apa  = data_block[idx_apa - 1]
                b_urban= data_block[idx_urban - 1]
                
                # Inițializăm cu 1 (True - Construibil)
                construibil = np.ones(b_drum.shape, dtype=np.uint8)
                
                # APLICĂM REGULILE DE EXCLUDERE (False = 0)
                # Obstacole directe (-1 înseamnă "pe obiect")
                construibil[b_drum == -1] = 0
                construibil[b_rail == -1] = 0
                construibil[b_apa == -1]  = 0
                construibil[b_urban == -1]= 0
                
                # Pădurea Adâncă (tăiem bucata din masca globală)
                r_start = window.row_off
                r_end = r_start + window.height
                c_start = window.col_off
                c_end = c_start + window.width
                
                block_padure_adanca = mask_padure_adanca[r_start:r_end, c_start:c_end]
                
                # Unde e pădure adâncă, punem 0
                construibil[block_padure_adanca] = 0
                
                # 4. Scriem noul strat (Ultima bandă - index 6)
                dst.write(construibil, window=window, indexes=profile['count'])

    print(f"\n✅ SUCCES! Fișierul '{OUTPUT_FILE}' are acum {profile['count']} benzi.")
    print("Ultima bandă este masca 'Construibil'.")

# Funcție de test
def test_interogare(row, col):
    if not Path(OUTPUT_FILE).exists(): return
    with rasterio.open(OUTPUT_FILE) as src:
        window = rasterio.windows.Window(col, row, 1, 1)
        vals = src.read(window=window)
        # Ultima valoare e construibil
        is_buildable = bool(vals[-1][0][0])
        print(f"\nPixel [{row}, {col}]:")
        print(f"  Construibil: {'DA' if is_buildable else 'NU (Restricționat)'}")
        
        descriptions = src.descriptions
        # Verificăm de ce nu e construibil
        if not is_buildable:
            found_reason = False
            for i, val in enumerate(vals[:-1]):
                val_num = val[0][0]
                if val_num == -1:
                    print(f"  - Blocat de: {descriptions[i]}")
                    found_reason = True
            if not found_reason:
                print("  - Blocat de: Pădure Adâncă (Eroziune)")

if __name__ == "__main__":
    calculeaza_construibil()
    test_interogare(12000, 12000)