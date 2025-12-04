import rasterio
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import numpy as np
from pathlib import Path

# Fișierul pe care îl verificăm
INPUT_FILE = "MASTER_DATASET_EXTENDED.tif"

# Coordonatele unde punem "Lupa" (Pixeli)
# 12000, 12000 este aproximativ centrul hărții.
# Poți modifica valorile dacă nimerești într-o zonă pustie.
CENTER_ROW = 12000
CENTER_COL = 12000
ZOOM_SIZE = 500  # Vedem un pătrat de 500x500 pixeli (5x5 km)

def microscop_harta():
    if not Path(INPUT_FILE).exists():
        print(f"EROARE: Nu găsesc '{INPUT_FILE}'")
        return

    print(f"🔍 INSPECTĂM O ZONĂ DE {ZOOM_SIZE}x{ZOOM_SIZE} PIXELI...")
    print(f"   La coordonatele: Rând {CENTER_ROW}, Coloană {CENTER_COL}")

    with rasterio.open(INPUT_FILE) as src:
        # 1. Definim Fereastra de Citire (Window)
        # Asta ne permite să citim doar bucățica mică, la rezoluție maximă
        window = rasterio.windows.Window(CENTER_COL, CENTER_ROW, ZOOM_SIZE, ZOOM_SIZE)
        
        # 2. Citim Banda 1 (Distanța Drumuri) - ca să vedem unde e drumul
        drumuri_dist = src.read(1, window=window)
        
        # 3. Citim Ultima Bandă (Masca Construibil) - ca să vedem restricția
        idx_construibil = src.count
        masca_construibil = src.read(idx_construibil, window=window)

    # --- VIZUALIZARE COMPARATIVĂ ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # STÂNGA: Unde este drumul fizic?
    # Afișăm distanța. Cu cât e mai albastru închis, cu atât e mai aproape de drum.
    # vmin=-1 (pe drum), vmax=50 (500m distanță)
    im1 = ax1.imshow(drumuri_dist, cmap='turbo', vmin=-1, vmax=50)
    ax1.set_title("Realitatea din Teren (Distanța Rutieră)\nLiniile închise sunt drumurile", fontsize=12)
    plt.colorbar(im1, ax=ax1, label="Distanță (decametri)")

    # DREAPTA: Cum a decis algoritmul?
    # Roșu = Interzis, Verde = Permis
    cmap_binar = ListedColormap(['#ff0000', '#00ff00']) # Roșu, Verde
    ax2.imshow(masca_construibil, cmap=cmap_binar, vmin=0, vmax=1, interpolation='nearest')
    ax2.set_title("Decizia Algoritmului (Masca Construibil)\nVerifică dacă linia roșie e continuă", fontsize=12)

    # Legendă Dreapta
    red_patch = mpatches.Patch(color='#ff0000', label='Interzis (0)')
    green_patch = mpatches.Patch(color='#00ff00', label='Construibil (1)')
    ax2.legend(handles=[red_patch, green_patch], loc='upper right')

    plt.tight_layout()
    print("Afișez graficele...")
    plt.show()

if __name__ == "__main__":
    microscop_harta()