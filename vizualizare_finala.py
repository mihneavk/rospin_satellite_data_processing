import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import numpy as np
from pathlib import Path

# --- CONFIGURARE ---
INPUT_FILE = "MASTER_DATASET_EXTENDED.tif"
SCALE_FACTOR = 0.05 # Citim doar 5% din pixeli pentru viteză

def visualize_buildable():
    if not Path(INPUT_FILE).exists():
        print(f"EROARE: Nu găsesc '{INPUT_FILE}'. Rulează întâi calculul.")
        return

    print(f"--- Pregătesc vizualizarea pentru '{INPUT_FILE}' ---")

    with rasterio.open(INPUT_FILE) as src:
        # 1. Identificăm ultima bandă (cea de construibil)
        buildable_band_idx = src.count
        band_description = src.descriptions[buildable_band_idx-1]
        print(f"Citesc Banda {buildable_band_idx}: {band_description}")

        # 2. Calculăm noile dimensiuni (Downsampling)
        new_height = int(src.height * SCALE_FACTOR)
        new_width = int(src.width * SCALE_FACTOR)
        print(f"Redimensionez de la {src.width}x{src.height} la {new_width}x{new_height}...")

        # 3. Citim datele folosind 'nearest' resampling
        # Este CRITIC să folosim 'nearest' pentru date booleene (0/1).
        # Altfel, 'bilinear' ar inventa valori gen 0.5 la granițe.
        mask_data = src.read(
            buildable_band_idx,
            out_shape=(new_height, new_width),
            resampling=Resampling.nearest
        )

    print("Generez imaginea...")
    
    # --- CONFIGURARE GRAFIC ---
    plt.figure(figsize=(12, 12))
    
    # Definim o paletă de culori strictă: 0=Roșu, 1=Verde
    cmap = ListedColormap(['#ff0000', '#00ff00'])
    
    # Afișăm imaginea
    # vmin=0, vmax=1 asigură că roșu e mereu 0 și verde e mereu 1,
    # chiar dacă în imaginea micșorată ar lipsi una dintre valori.
    plt.imshow(mask_data, cmap=cmap, vmin=0, vmax=1, interpolation='nearest')
    
    # Adăugăm titlu și legendă
    plt.title("Harta Zonelor Construibile (Masca Finală)\nRegiunea Nord-Est", fontsize=16, fontweight='bold')
    plt.axis('off') # Ascundem axele cu coordonate

    # Legendă manuală
    red_patch = mpatches.Patch(color='#ff0000', label='Restricționat (0)\n(Obstacole sau Pădure Adâncă)')
    green_patch = mpatches.Patch(color='#00ff00', label='Construibil (1)')
    plt.legend(handles=[green_patch, red_patch], loc='upper right', fontsize=12, frameon=True)
    
    print("Afișez fereastra...")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    visualize_buildable()