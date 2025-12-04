import rasterio
import numpy as np
from scipy.ndimage import distance_transform_cdt
import time

fisier_drumuri = "matrice_drumuri_10m.tif"
fisier_distante = "matrice_distanta_drum.tif"

print(f"--- 1. Încărcăm matricea de drumuri ---")
with rasterio.open(fisier_drumuri) as src:
    # Citim matricea (Drum=1, Câmp=0)
    matrice_drumuri = src.read(1)
    profile = src.profile
    
    # Salvăm metadatele pentru scrierea ulterioară
    # Trebuie să schimbăm tipul de date în int16 pentru a permite valori negative (-1)
    profile.update(dtype=rasterio.int16, count=1, compress='lzw')

print("--- 2. Pregătim calculul distanței ---")
# Algoritmul scipy calculează distanța de la punctele NON-ZERO până la cel mai apropiat ZERO.
# Noi vrem distanța de la CÂMP la cel mai apropiat DRUM.
# Deci:
#   - Drumurile trebuie să fie 0 (Ținta)
#   - Câmpul trebuie să fie 1 (Zona de calculat)

# Inversăm logica: Unde e drum (1) devine False(0), unde e câmp (0) devine True(1)
matrice_binara_inversa = (matrice_drumuri == 0)

print("--- 3. Rulăm Transformata Distanței (Chessboard) ---")
start_time = time.time()

# metric='chessboard' înseamnă că se măsoară în pași de rege pe tabla de șah (inclusiv diagonale)
# Asta corespunde cerinței tale de "straturi" de pixeli.
distante_raw = distance_transform_cdt(matrice_binara_inversa, metric='chessboard')

end_time = time.time()
print(f"Calculul a durat: {end_time - start_time:.2f} secunde.")

print("--- 4. Aplicăm formula ta personalizată (Offset) ---")
# Acum avem: Drum=0, Vecin=1, Vecin2=2...
# Tu vrei:   Drum=-1, Vecin=0, Vecin2=1...
# Deci scădem 1 din toată matricea.
# Convertim la int16 pentru a permite numere negative
matrice_finala = distante_raw.astype(np.int16) - 1

# Verificare rapidă
print("\nVerificare valori:")
min_val = matrice_finala.min()
max_val = matrice_finala.max()
print(f"  Minim (ar trebui să fie -1): {min_val}")
print(f"  Maxim (cel mai izolat punct): {max_val} (adică {max_val * 10} metri de un drum)")

print("--- 5. Salvăm rezultatul ---")
with rasterio.open(fisier_distante, 'w', **profile) as dst:
    dst.write(matrice_finala, 1)

print(f"Gata! Fișierul '{fisier_distante}' a fost salvat.")