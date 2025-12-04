import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors
from pathlib import Path

# --- CONFIGURARE ---
INPUT_FILE = "MATRICE_SCOR_FINAL.tif"
SCALE_FACTOR = 0.05  # Citim 5% din pixeli pentru viteză

def vizualizeaza_scor():
    if not Path(INPUT_FILE).exists():
        print(f"EROARE: Nu găsesc '{INPUT_FILE}'. Rulează calculul de scor mai întâi.")
        return

    print(f"--- Pregătesc vizualizarea Heatmap pentru '{INPUT_FILE}' ---")

    with rasterio.open(INPUT_FILE) as src:
        # Calculăm dimensiunile reduse
        new_height = int(src.height * SCALE_FACTOR)
        new_width = int(src.width * SCALE_FACTOR)
        print(f"Redimensionez la {new_width}x{new_height}...")

        # Citim datele (Nearest neighbor pentru a nu altera valorile discrete gen -1)
        data = src.read(
            1,
            out_shape=(new_height, new_width),
            resampling=Resampling.nearest
        )

    print("Generez graficul...")

    # --- PREGĂTIREA DATELOR PENTRU PLOT ---
    # 1. Mascăm zonele interzise (-1) pentru a le colora separat
    # np.ma.masked_equal ascunde valorile egale cu -1 din harta de culori principală
    data_scoruri = np.ma.masked_equal(data, -1)

    # 2. Creăm o mască doar pentru zonele interzise (pentru fundal)
    mask_interzis = (data == -1)

    # --- CONFIGURARE GRAFIC ---
    plt.figure(figsize=(14, 12))
    
    # Stratul 1: Fundalul pentru zonele interzise (Gri închis)
    # Putem folosi imshow cu o hartă de culori solidă sau doar setăm background-ul,
    # dar desenarea unei măști gri e cea mai clară.
    cmap_interzis = mcolors.ListedColormap(['#404040']) # Gri închis
    plt.imshow(mask_interzis, cmap=cmap_interzis, interpolation='nearest')

    # Stratul 2: Scorurile (peste fundal)
    # Folosim 'turbo' sau 'jet' pentru contrast maxim între scor mic și mare
    # vmin=0, vmax=45 (Scorul maxim teoretic e 44)
    img = plt.imshow(data_scoruri, cmap='turbo', vmin=0, vmax=45, interpolation='nearest')

    # --- ELEMENTE VIZUALE ---
    plt.title("Harta Strategică Finală: Scor Tactic\n(Roșu = Locație Ideală, Gri = Interzis)", fontsize=16, fontweight='bold')
    plt.axis('off')

    # Bara de culori (doar pentru scoruri)
    cbar = plt.colorbar(img, orientation='vertical', fraction=0.03, pad=0.04)
    cbar.set_label('Punctaj Tactic (0 - 45)', fontsize=12, labelpad=15)
    
    # Adăugăm manual eticheta pentru zona gri în legendă
    import matplotlib.patches as mpatches
    grey_patch = mpatches.Patch(color='#404040', label='Zonă Restricționată (-1)')
    plt.legend(handles=[grey_patch], loc='upper left', frameon=True, fontsize=11)

    print("Afișez fereastra...")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    vizualizeaza_scor()