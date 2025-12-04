import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np

# Fișierul generat cu succes
FILE_PATH = "matrice_satelit_finala.tif"

# --- LEGENDA MILITARĂ ---
# Culorile corespund valorilor din matricea ta
legend_config = {
    -1: {"label": "CLĂDIRI / URBAN (Obstacol)", "color": "#000000"},  # Negru
    0:  {"label": "EXTERIOR (NoData)", "color": "#ffffff"},           # Alb
    2:  {"label": "APĂ (Obstacol Natural)", "color": "#1f77b4"},      # Albastru
    3:  {"label": "TUFIȘURI (Acoperire Medie)", "color": "#bcbd22"},  # Kaki
    5:  {"label": "PĂDURE (Camuflaj Bun)", "color": "#2ca02c"},       # Verde Pădure
    7:  {"label": "CÂMP DESCHIS (Expus)", "color": "#98df8a"}         # Verde Deschis
}

def visualize_map():
    print(f"--- Încărcăm '{FILE_PATH}'... ---")
    
    try:
        with rasterio.open(FILE_PATH) as src:
            print(f"Dimensiune originală: {src.width}x{src.height}")
            
            # Citim doar 5% din pixeli (Downsampling) pentru viteză
            scale = 0.05
            h, w = int(src.height * scale), int(src.width * scale)
            print(f"Redimensionăm pentru afișare la: {w}x{h}")

            # Folosim 'nearest' pentru a păstra culorile exacte
            data = src.read(1, out_shape=(h, w), resampling=Resampling.nearest)
            
    except FileNotFoundError:
        print(f"EROARE: Nu găsesc {FILE_PATH}")
        return

    print("--- Generăm imaginea color... ---")
    
    # Creăm imaginea RGB
    rgb_image = np.zeros((data.shape[0], data.shape[1], 3))
    unique_vals = np.unique(data)
    print(f"Valori prezente pe hartă: {unique_vals}")

    # Pictăm pixelii
    for val, props in legend_config.items():
        if val in unique_vals:
            rgb = mcolors.to_rgb(props["color"])
            rgb_image[data == val] = rgb

    # Afișăm
    plt.figure(figsize=(12, 10))
    plt.imshow(rgb_image)
    
    # Creăm legenda
    patches = [mpatches.Patch(color=legend_config[v]["color"], label=legend_config[v]["label"]) 
               for v in unique_vals if v in legend_config]
    
    plt.legend(handles=patches, loc='upper left', bbox_to_anchor=(1, 1))
    plt.title("Harta Tactică a Terenului\nRegiunea Nord-Est")
    plt.axis('off')
    
    print("Afișăm fereastra...")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    visualize_map()