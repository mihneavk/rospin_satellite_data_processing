import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
import numpy as np

fisier_distante = "matrice_distanta_drum.tif"

print("--- Pregătim vizualizarea (Interval 0 - 5 km)... ---")

with rasterio.open(fisier_distante) as src:
    # Păstrăm downsampling-ul pentru viteză
    scale_factor = 0.05
    new_height = int(src.height * scale_factor)
    new_width = int(src.width * scale_factor)
    
    print(f"Redimensionăm: {src.width}x{src.height} -> {new_width}x{new_height}")

    data = src.read(
        1,
        out_shape=(new_height, new_width),
        resampling=Resampling.nearest
    )

print("--- Generăm graficul... ---")

plt.figure(figsize=(12, 10))

# --- MODIFICARE: vmax=500 ---
# 500 pixeli * 10 metri = 5000 metri (5 km)
img = plt.imshow(data, cmap='turbo', vmin=-1, vmax=500)

cbar = plt.colorbar(img, label='Distanța (nr. pătrate)')
cbar.set_label('Distanța (valoare x 10m)', rotation=270, labelpad=15)

plt.title(f"Harta Accesibilității (Zoom pe zona 0 - 5 km)\nAlbastru = Lângă Drum | Roșu = Izolat (>5km)")
plt.axis('off')

print("Afișăm fereastra...")
plt.show()