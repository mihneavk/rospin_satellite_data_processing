import rasterio
import numpy as np
from scipy.ndimage import distance_transform_cdt
import time

# Fișiere
fisier_input_rail = "matrice_cai_ferate_10m.tif"
fisier_output_dist = "matrice_distanta_rail.tif"

print(f"--- 1. Încărcăm matricea căilor ferate ---")
try:
    with rasterio.open(fisier_input_rail) as src:
        # Citim datele
        matrice_rail = src.read(1)
        profile = src.profile
        
        # Actualizăm profilul pentru int16 (ca să suporte distanțe mari)
        profile.update(dtype=rasterio.int16, count=1, compress='lzw')

except FileNotFoundError:
    print(f"EROARE: Nu găsesc '{fisier_input_rail}'.")
    print("Verifică dacă ai rulat Pasul 7 sau dacă ești în folderul corect.")
    exit()

print("--- 2. Calculăm Transformata Distanței (Chessboard) ---")
# Inversăm logica: Șina(1) devine 0 (ținta), Câmpul(0) devine 1 (de calculat)
matrice_binara_inversa = (matrice_rail == 0)

start_time = time.time()

# Calculăm distanța
distante_raw = distance_transform_cdt(matrice_binara_inversa, metric='chessboard')

end_time = time.time()
print(f"Calculul a durat: {end_time - start_time:.2f} secunde.")

print("--- 3. Ajustăm valorile ---")
# Șina devine -1, Lângă șină devine 0, etc.
matrice_finala = distante_raw.astype(np.int16) - 1

# Verificare
max_dist = matrice_finala.max()
print(f"Cel mai izolat punct față de o gară este la: {max_dist * 10 / 1000:.1f} km")

print("--- 4. Salvăm Harta Distanțelor Feroviare ---")
with rasterio.open(fisier_output_dist, 'w', **profile) as dst:
    dst.write(matrice_finala, 1)

print(f"Gata! Ai generat '{fisier_output_dist}'.")