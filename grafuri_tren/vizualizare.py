import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
import numpy as np

fisier_distante = "matrice_distanta_rail.tif"

print("--- Pregătim vizualizarea (Limită 7.5 km)... ---")

try:
    with rasterio.open(fisier_distante) as src:
        scale_factor = 0.05
        new_height = int(src.height * scale_factor)
        new_width = int(src.width * scale_factor)
        
        print(f"Redimensionăm: {src.width}x{src.height} -> {new_width}x{new_height}")

        data = src.read(
            1,
            out_shape=(new_height, new_width),
            resampling=Resampling.nearest
        )
except FileNotFoundError:
    print(f"EROARE: Nu găsesc '{fisier_distante}'.")
    exit()

print("--- Generăm graficul... ---")

plt.figure(figsize=(12, 10))

# --- MODIFICARE: vmax=750 ---
# 750 pixeli * 10 metri = 7500 metri (7.5 km)
img = plt.imshow(data, cmap='turbo', vmin=-1, vmax=750)

cbar = plt.colorbar(img, label='Distanța')
cbar.set_label('Distanța (valoare x 10m)', rotation=270, labelpad=15)

plt.title(f"Harta Accesibilității Feroviare (Nord-Est)\nAlbastru = Lângă Șină | Roșu = >7.5 km distanță")
plt.axis('off')

print("Afișăm fereastra...")
plt.show()