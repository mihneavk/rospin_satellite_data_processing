import rasterio
import numpy as np
from scipy.ndimage import distance_transform_cdt
import time
from pathlib import Path
import sys



if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# --- CONFIGURARE ---
INPUT_FILE = "matrice_satelit_finala.tif"

# Definim ce categorii ne interesează pentru calculul distanței
# Cheia este valoarea din hartă, Valoarea este numele fișierului
TARGETS = [
    {"valoare": 5,  "nume": "padure", "desc": "Pădure (Camuflaj)"},
    {"valoare": 2,  "nume": "apa",    "desc": "Apă (Resursă/Obstacol)"},
    {"valoare": -1, "nume": "urban",  "desc": "Urban (Clădiri)"}
]

def genereaza_harta_distanta(input_path, valoare_tinta, nume_iesire):
    print(f"\n--- Procesare: Distanța față de {nume_iesire.upper()} ---")
    
    with rasterio.open(input_path) as src:
        # Citim datele
        matrice = src.read(1)
        profile = src.profile
        
        # Pregătim profilul pentru output (int16 pentru distanțe mari)
        profile.update(dtype=rasterio.int16, count=1, compress='lzw', nodata=None)

        # 1. Creăm Masca Binară
        # Vrem distanța până la pixelii care au 'valoare_tinta'
        # Logica scipy: 0 = Țintă (Obstacol), 1 = Spațiu gol (de calculat)
        
        # Deci: Unde este ținta punem 0, în rest punem 1
        mask = (matrice != valoare_tinta).astype(np.int8)
        
        # Verificăm dacă există ținta pe hartă
        if np.sum(mask == 0) == 0:
            print(f"⚠️ ATENȚIE: Nu există nicio zonă de tip '{nume_iesire}' pe hartă!")
            return

        # 2. Calculăm Transformata Distanței (Chessboard)
        # metric='chessboard' -> pași de 10m (inclusiv diagonale)
        start = time.time()
        distante = distance_transform_cdt(mask, metric='chessboard')
        print(f"  Calcul realizat în {time.time() - start:.2f} secunde.")

        # 3. Ajustăm valorile (Formatul tău standard)
        # Ținta devine -1, Vecinul 0, etc.
        matrice_finala = distante.astype(np.int16) - 1
        
        # Mascăm zona din afara județelor (unde originalul era 0 și nu e țintă)
        # Dacă originalul e 0 (NoData) și nu calculăm distanța față de NoData, 
        # ar fi bine să punem o valoare mare sau să lăsăm calculul.
        # Strategie: Lăsăm calculul valid, dar ținem cont că 0 exterior e "infinit".
        # Totuși, algoritmul va calcula distanța din interior spre exterior.
        
        # Opțional: Putem forța 0 exterior să fie o valoare maximă, 
        # dar pentru moment lăsăm matematica pură.

        # 4. Salvare
        output_filename = f"matrice_distanta_{nume_iesire}.tif"
        with rasterio.open(output_filename, 'w', **profile) as dst:
            dst.write(matrice_finala, 1)
            
        print(f"✅ Salvat: {output_filename}")
        print(f"  Max Dist: {np.max(matrice_finala) * 10 / 1000:.1f} km")

if __name__ == "__main__":
    
    if not Path(INPUT_FILE).exists():
        print(f"EROARE: Nu găsesc fișierul '{INPUT_FILE}'")
        exit()

    print(f"Începem propagarea pentru fișierul: {INPUT_FILE}")

    for target in TARGETS:
        genereaza_harta_distanta(
            INPUT_FILE, 
            target["valoare"], 
            target["nume"]
        )

    print("\nToate hărțile de distanță au fost generate!")