import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# --- CONFIGURARE ---
# Lista fișierelor de vizualizat și titlurile lor
FILES_TO_PLOT = [
    {"path": "matrice_distanta_padure.tif", "title": "1. Acces Camuflaj (Pădure)"},
    {"path": "matrice_distanta_apa.tif",    "title": "2. Acces Resurse (Apă)"},
    {"path": "matrice_distanta_urban.tif",  "title": "3. Proximitate Civilă (Orașe)"}
]

# Limita de vizualizare (ca să nu fie totul roșu)
# 500 de unități * 10m = 5000m = 5 km
# Tot ce e mai departe de 5km va fi roșu aprins.
VMAX_LIMIT = 500 

def plot_side_by_side():
    print("--- Pregătim vizualizarea comparativă (Panou 1x3) ---")
    
    # Creăm o figură lată cu 3 subplot-uri unul lângă altul
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    # Aplatizăm vectorul de axe pentru iterare ușoară
    axes = axes.flatten()

    colormap = 'turbo' # O paletă de culori foarte clară (curcubeu modern)
    images = [] # Păstrăm referința pentru bara de culori comună

    for i, file_info in enumerate(FILES_TO_PLOT):
        fpath = file_info["path"]
        ax = axes[i]
        
        if not Path(fpath).exists():
            print(f"⚠️ EROARE: Nu găsesc {fpath}. Sar peste.")
            ax.text(0.5, 0.5, "Fișier Lipsă", ha='center')
            ax.axis('off')
            continue
            
        print(f"Încarc: {fpath}...")
        with rasterio.open(fpath) as src:
            # Downsampling pentru viteză (citim 5% din mărime)
            scale = 0.05
            h, w = int(src.height * scale), int(src.width * scale)
            
            # Folosim 'bilinear' pentru că datele de distanță sunt continue (netede)
            data = src.read(1, out_shape=(h, w), resampling=Resampling.bilinear)
            
            # Desenăm harta pe axa curentă
            # vmin=-1 asigură că interiorul obiectivului are cea mai închisă culoare
            im = ax.imshow(data, cmap=colormap, vmin=-1, vmax=VMAX_LIMIT)
            images.append(im)
            
            ax.set_title(file_info["title"], fontsize=12, fontweight='bold')
            ax.axis('off') # Ascundem coordonatele pixelilor

    # --- Adăugăm o Bară de Culori (Colorbar) comună în dreapta ---
    # Ajustăm spațiul din figură pentru a face loc barei
    fig.subplots_adjust(right=0.9)
    # Definim poziția barei: [stânga, jos, lățime, înălțime]
    cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    
    cbar = fig.colorbar(images[0], cax=cbar_ax)
    cbar.set_label('Distanța (decametri - pași de 10m)\nRoșu intens > 5km', rotation=270, labelpad=25, fontsize=10)

    plt.suptitle("Analiză Strategică Comparativă: Moldova Nord-Est\n(Zonele albastre sunt țintele, zonele roșii sunt izolate)", fontsize=16, y=0.98)
    
    print("Afișăm fereastra...")
    plt.show()

if __name__ == "__main__":
    plot_side_by_side()