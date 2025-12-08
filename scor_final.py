import rasterio
import numpy as np
import os
from pathlib import Path

# --- CONFIGURARE ---
INPUT_FILE = "MASTER_DATASET_EXTENDED.tif"
OUTPUT_FILE = "MATRICE_SCOR_FINAL.tif"

def calculeaza_scor():
    if not Path(INPUT_FILE).exists():
        print(f"EROARE: Nu găsesc '{INPUT_FILE}'")
        return

    # Ștergem fișierul vechi dacă există
    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
        except PermissionError:
            print(f"EROARE: Închide fișierul '{OUTPUT_FILE}' din alte programe!")
            return

    print(f"--- Încep calculul scorului GRADUAL pe baza ponderilor liniare ---")

    with rasterio.open(INPUT_FILE) as src:
        # Verificăm dacă avem toate cele 6 benzi
        if src.count < 6:
            print(f"EROARE: Fișierul are doar {src.count} benzi. Rulează scriptul de 'Construibil' înainte!")
            return

        # Pregătim profilul pentru output
        # Scor maxim posibil: 40 (Rail) + 35 (Drum) + 12 (Apa) + 23 (Padure) = 110. 
        # int8 (max 127) este suficient.
        profile = src.profile.copy()
        profile.update(
            count=1,
            dtype=rasterio.int8,
            compress='lzw',
            BIGTIFF='YES',
            nodata=-1 # Folosim -1 pentru neconstruibil
        )

        # Indecșii benzilor (1-based)
        IDX_DRUM = 1
        IDX_RAIL = 2
        IDX_PADURE = 3
        IDX_APA = 4
        IDX_CONSTRUIBIL = 6

        with rasterio.open(OUTPUT_FILE, 'w', **profile) as dst:
            dst.set_band_description(1, "Scor Tactic Final Gradual (Max 110p)")

            # Procesăm pe blocuri (ferestre) pentru eficiență memorie
            windows = [window for ij, window in dst.block_windows(1)]
            print(f"Procesez {len(windows)} blocuri de date...")

            # Încercăm să folosim tqdm pentru progress bar
            try:
                from tqdm import tqdm
                iterator = tqdm(windows)
            except ImportError:
                iterator = windows

            for window in iterator:
                # Citim datele necesare
                dist_drum = src.read(IDX_DRUM, window=window)
                dist_rail = src.read(IDX_RAIL, window=window)
                dist_padure = src.read(IDX_PADURE, window=window)
                dist_apa = src.read(IDX_APA, window=window)
                mask_construibil = src.read(IDX_CONSTRUIBIL, window=window)

                # Inițializăm matricea de scor cu 0 (float pentru calcul precis, apoi convertim)
                scor = np.zeros(dist_drum.shape, dtype=np.float32)
                
                # --- NOU: CALCUL SCOR GRADUAL CU INTERPOLARE (np.interp) ---
                # np.interp funcționează liniar între punctele date (XP, FP)

                # --- 1. CALE FERATĂ (Band 2) - Gradual (Max 40p) ---
                # Noduri de distanță (pixeli, 10m/unitate): 0, 1, 10, 50, 150, 151
                xp_rail = np.array([0, 1, 10, 50, 150, 151])
                # Scoruri: 0 la fix, 40 la 10m-100m, scade la 15 la 500m, etc.
                fp_rail = np.array([0, 40, 40, 15, 5, 0]) 
                
                # numpy interp funcționează corect și pe matrice 2D în versiunile noi
                scor += np.interp(dist_rail, xp_rail, fp_rail)

                # --- 2. DRUM (Band 1) - Gradual (Max 35p) ---
                # Puncte: 0m, 10m, 50m, 200m, 700m, 2000m
                xp_drum = np.array([0, 1, 5, 20, 70, 200, 201])
                fp_drum = np.array([0, 35, 35, 20, 10, 3, 0]) 

                scor += np.interp(dist_drum, xp_drum, fp_drum)

                # --- 3. APĂ (Band 4) - Gradual (Max 12p) ---
                # Puncte: 0m, 30m, 40m, 100m, 300m, 600m
                xp_apa = np.array([0, 3, 4, 10, 30, 60, 61])
                fp_apa = np.array([0, 0, 12, 12, 5, 2, 0])

                scor += np.interp(dist_apa, xp_apa, fp_apa)
                
                # --- 4. PĂDURE (Band 3) - Fix + Margine (Max 23p) ---
                # 4a. Scor maxim dacă pixelul e ÎN pădure (-1)
                scor_padure = np.where(dist_padure == -1, 23.0, 0.0)
                
                # 4b. Bonus de margine (Liziera): 15p dacă ești la 10m-50m de pădure
                # Doar unde nu e deja în pădure
                scor_padure += np.where((dist_padure >= 1) & (dist_padure <= 5) & (dist_padure != -1), 15.0, 0.0)
                
                scor += scor_padure

                # --- 5. APLICARE MASCĂ CONSTRUIBIL (Band 6) ---
                # Rotunjim scorul total și îl convertim la int8
                scor_final = scor.round().astype(np.int8)

                # Dacă nu e construibil (0), scorul devine -1
                scor_final = np.where(mask_construibil == 1, scor_final, -1)

                # Scriem rezultatul
                dst.write(scor_final, window=window, indexes=1)

    print(f"\n✅ SUCCES! Matricea de scor GRADUAL a fost salvată în '{OUTPUT_FILE}'.")

def test_pixel(row, col):
    if not Path(OUTPUT_FILE).exists(): return
    with rasterio.open(OUTPUT_FILE) as src:
        # Citim la poziția specificată (col, row, 1, 1)
        try:
            val = src.read(1, window=rasterio.windows.Window(col, row, 1, 1))[0][0]
            print(f"Scor GRADUAL la pixelul [{row}, {col}]: {val}")
        except Exception:
            print(f"Atenție: Pixelul [{row}, {col}] este în afara domeniului.")

if __name__ == "__main__":
    calculeaza_scor()
    # Testăm un punct (ex: mijlocul hărții)
    test_pixel(12000, 12000)