import argparse
import rasterio
import matplotlib.pyplot as plt
import numpy as np
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from pathlib import Path
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches

# --- CONFIGURARE ---
INPUT_FILE = "MATRICE_SCOR_FINAL.tif"
OUTPUT_PNG = "zona_selectata.png"

def extract_region(lat1, lon1, lat2, lon2):
    if not Path(INPUT_FILE).exists():
        print(f"EROARE: Nu găsesc fișierul '{INPUT_FILE}'")
        return

    print(f"--- Extragere Zonă (cu Legendă) ---")
    print(f"Coordonate: {lat1}, {lon1} <-> {lat2}, {lon2}")

    with rasterio.open(INPUT_FILE) as src:
        # 1. Calculăm limitele
        south, north = min(lat1, lat2), max(lat1, lat2)
        west, east = min(lon1, lon2), max(lon1, lon2)

        try:
            left, bottom, right, top = transform_bounds(
                "EPSG:4326", src.crs, west, south, east, north
            )
        except Exception as e:
            print(f"Eroare conversie coordonate: {e}")
            return

        # 2. Calculăm fereastra
        window = from_bounds(left, bottom, right, top, transform=src.transform)
        window = window.round_offsets().round_lengths()
        
        # 3. Citim datele
        try:
            data = src.read(1, window=window)
        except Exception:
            print("EROARE: Coordonate în afara hărții.")
            return

        if data.size == 0:
            print("EROARE: Zonă goală.")
            return

    # --- VIZUALIZARE ---
    print("Generez imaginea...")
    
    # Creăm o figură mai lată pentru a face loc legendei
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # A. FUNDALUL GRI (Zone Interzise: -1)
    mask_interzis = (data == -1)
    cmap_interzis = mcolors.ListedColormap(['#404040']) # Gri închis
    ax.imshow(mask_interzis, cmap=cmap_interzis, interpolation='nearest', aspect='auto')

    # B. SCORURILE (0 - 45)
    data_masked = np.ma.masked_equal(data, -1)
    im = ax.imshow(data_masked, cmap='turbo', vmin=0, vmax=45, interpolation='nearest', aspect='auto')

    # Ascundem axele X/Y (coordonatele pixelilor nu sunt relevante vizual)
    ax.set_axis_off()
    ax.set_title(f"Analiză Tactică Zonă\n", fontsize=14, fontweight='bold', pad=20)

    # --- LEGENDA 1: Bara de Culori (Scor) ---
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Punctaj Tactic (0 - 45)', rotation=270, labelpad=15, fontsize=10)
    
    # --- LEGENDA 2: Zona Interzisă ---
    # Creăm un "patch" (pătrățel de culoare) manual
    grey_patch = mpatches.Patch(color='#404040', label='Zonă Restricționată\n(Drum/Apă/Urban/Pădure)')
    
    # Adăugăm legenda în colțul din stânga sus (sau unde dorești)
    # bbox_to_anchor o scoate puțin în afara hărții ca să nu acopere datele
    plt.legend(handles=[grey_patch], loc='upper left', bbox_to_anchor=(0, 1.05), frameon=True)

    # Salvăm
    plt.savefig(OUTPUT_PNG, bbox_inches='tight', dpi=150)
    plt.close()
    
    print(f"✅ SUCCES! Imaginea salvată ca: '{OUTPUT_PNG}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("lat1", type=float)
    parser.add_argument("lon1", type=float)
    parser.add_argument("lat2", type=float)
    parser.add_argument("lon2", type=float)
    args = parser.parse_args()

    extract_region(args.lat1, args.lon1, args.lat2, args.lon2)