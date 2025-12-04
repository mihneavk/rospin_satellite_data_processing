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

    print(f"--- Încep calculul scorului pe baza regulilor tale ---")

    with rasterio.open(INPUT_FILE) as src:
        # Verificăm dacă avem toate cele 6 benzi
        if src.count < 6:
            print(f"EROARE: Fișierul are doar {src.count} benzi. Rulează scriptul de 'Construibil' înainte!")
            return

        # Pregătim profilul pentru output
        # Vom avea o singură bandă cu scorul (int8 e suficient: -1 până la 100)
        profile = src.profile.copy()
        profile.update(
            count=1,
            dtype=rasterio.int8,
            compress='lzw',
            BIGTIFF='YES',
            nodata=-128 # Valoare tehnică pentru erori, dar noi folosim -1 pentru neconstruibil
        )

        # Indecșii benzilor (1-based)
        IDX_DRUM = 1
        IDX_RAIL = 2
        IDX_PADURE = 3
        IDX_APA = 4
        IDX_CONSTRUIBIL = 6

        with rasterio.open(OUTPUT_FILE, 'w', **profile) as dst:
            dst.set_band_description(1, "Scor Tactic Final")

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
                # Read returnează (bands, h, w), noi vrem doar matricea (h, w)
                dist_drum = src.read(IDX_DRUM, window=window)
                dist_rail = src.read(IDX_RAIL, window=window)
                dist_padure = src.read(IDX_PADURE, window=window)
                dist_apa = src.read(IDX_APA, window=window)
                mask_construibil = src.read(IDX_CONSTRUIBIL, window=window)

                # Inițializăm matricea de scor cu 0
                scor = np.zeros(dist_drum.shape, dtype=np.int8)

                # --- 1. REGULI DRUM (Band 1) ---
                # < 40m (4 unități): 0 puncte (deja 0)
                # 40m - 200m (4 - 20 unități): 15 puncte
                scor += np.where((dist_drum >= 4) & (dist_drum < 20), 15, 0).astype(np.int8)
                # 200m - 700m (20 - 70 unități): 8 puncte
                scor += np.where((dist_drum >= 20) & (dist_drum < 70), 8, 0).astype(np.int8)

                # --- 2. REGULI TREN (Band 2) ---
                # 40m - 1000m (4 - 100 unități): 20 puncte
                scor += np.where((dist_rail >= 4) & (dist_rail < 100), 20, 0).astype(np.int8)
                # 1000m - 3000m (100 - 300 unități): 15 puncte
                scor += np.where((dist_rail >= 100) & (dist_rail < 300), 15, 0).astype(np.int8)
                # 3000m - 10000m (300 - 1000 unități): 8 puncte
                scor += np.where((dist_rail >= 300) & (dist_rail < 1000), 8, 0).astype(np.int8)

                # --- 3. REGULI APĂ (Band 4) ---
                # 40m - 300m (4 - 30 unități): 5 puncte
                scor += np.where((dist_apa >= 4) & (dist_apa < 30), 5, 0).astype(np.int8)

                # --- 4. REGULI PĂDURE (Band 3) ---
                # Dacă e pădure (-1): 4 puncte
                # Notă: Dacă e pădure adâncă, oricum va fi tăiat de masca construibil,
                # dar pentru marginile construibile ale pădurii, primești puncte.
                scor += np.where(dist_padure == -1, 4, 0).astype(np.int8)

                # --- 5. APLICARE MASCĂ CONSTRUIBIL (Band 6) ---
                # Dacă nu e construibil (0), scorul devine -1
                scor = np.where(mask_construibil == 1, scor, -1)

                # Scriem rezultatul
                dst.write(scor, window=window, indexes=1)

    print(f"\n✅ SUCCES! Matricea de scor a fost salvată în '{OUTPUT_FILE}'.")

def test_pixel(row, col):
    if not Path(OUTPUT_FILE).exists(): return
    with rasterio.open(OUTPUT_FILE) as src:
        val = src.read(1, window=rasterio.windows.Window(col, row, 1, 1))[0][0]
        print(f"Scor la pixelul [{row}, {col}]: {val}")

if __name__ == "__main__":
    calculeaza_scor()
    # Testăm un punct (ex: mijlocul hărții)
    test_pixel(12000, 12000)