import rasterio
import numpy as np
from pathlib import Path

# --- Setări ---
# Presupunem că scriptul rulează din același loc ca înainte
# și că fișierul .tif este deja dezarhivat în ./tmp/numele_folderului/
base_folder = "./tmp"
folder_name = "CLMS_CLCPLUS_RAS_S2023_R10m_E54N27_03035_V01_R00"
tif_name = folder_name + ".tif"

# Construim calea completă către fișierul .tif
tif_path = Path(base_folder) / folder_name / tif_name

# --- Încărcarea matricii ---
try:
    with rasterio.open(tif_path) as dataset:
        
        # 1. Citim prima (și singura) bandă a fișierului
        # Aceasta încarcă ÎNTREAGA imagine în memorie!
        matrice_valori = dataset.read(1)
        
        # 2. Afișăm informații despre matrice
        print(f"Matricea a fost încărcată cu succes!")
        print(f"Forma matricii (rânduri, coloane): {matrice_valori.shape}")
        print(f"Tipul de date al valorilor: {matrice_valori.dtype}")
        
        # 3. Afișăm un mic eșantion (primele 5 rânduri și 5 coloane)
        print("\nEșantion (colțul stânga-sus):")
        print(matrice_valori[0:50, 0:50])

except FileNotFoundError:
    print(f"EROARE: Fișierul .tif nu a fost găsit la: {tif_path}")
    print("Asigură-te că ai rulat scriptul anterior pentru a dezarhiva fișierul.")
except Exception as e:
    print(f"A apărut o eroare: {e}")