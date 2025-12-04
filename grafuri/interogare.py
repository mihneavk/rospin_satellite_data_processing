import rasterio
import numpy as np

fisier_matrice = "matrice_drumuri_10m.tif"

print(f"--- Încărcăm matricea din '{fisier_matrice}' ---")

with rasterio.open(fisier_matrice) as src:
    # 1. Citim datele într-un array Numpy
    # indexul 1 înseamnă prima 'bandă' de date (fișierul are doar una)
    matrice = src.read(1)
    
    # Salvăm transformarea pentru a putea converti Lat/Lon în Pixel
    transform = src.transform
    crs = src.crs
    
    # Dimensiuni
    inaltime, latime = matrice.shape
    
print(f"Dimensiuni matrice: {inaltime} linii x {latime} coloane")
print(f"Total celule (pătrate de 10x10m): {matrice.size:,}")

# Calculăm statistici
numar_drumuri = np.count_nonzero(matrice == 1)
procent_drumuri = (numar_drumuri / matrice.size) * 100

print(f"\nStatistici:")
print(f"Celule cu drum (valoare 1): {numar_drumuri:,}")
print(f"Celule câmp (valoare 0): {matrice.size - numar_drumuri:,}")
print(f"Densitate rutieră: {procent_drumuri:.2f}% din suprafață este acoperită de drumuri/buffer.")

# --- INTEROGARE PUNCTUALĂ ---
# Funcție care transformă Lat/Lon (Google Maps) în rând/coloană matrice
def verifica_locatie(lat, lon, dataset_reader):
    # Trebuie să transformăm Lat/Lon (WGS84) în coordonatele fișierului (UTM)
    # Folosim o transformare internă a rasterio
    from rasterio.warp import transform as warp_transform
    
    # Fișierul nostru e în UTM (metric), inputul e în Lat/Lon (grade)
    # CRS-ul sursă e WGS84 (EPSG:4326), CRS-ul destinație e cel al fișierului
    xs, ys = warp_transform('EPSG:4326', dataset_reader.crs, [lon], [lat])
    x_utm, y_utm = xs[0], ys[0]
    
    # Obținem rândul și coloana din matrice
    row, col = dataset_reader.index(x_utm, y_utm)
    
    return row, col

print("\n--- TEST: Verificăm o locație reală ---")
# Exemplu: Palatul Culturii Iași (ar trebui să fie lângă drum)
lat_test = 47.1614
lon_test = 27.5835

# Trebuie să redeschidem 'src' pentru a folosi metodele de transformare
with rasterio.open(fisier_matrice) as src:
    r, c = verifica_locatie(lat_test, lon_test, src)
    
    # Verificăm limitele (să nu fim în afara hărții)
    if 0 <= r < inaltime and 0 <= c < latime:
        valoare = matrice[r, c]
        tip = "DRUM" if valoare == 1 else "CÂMP"
        print(f"Coordonate: {lat_test}, {lon_test}")
        print(f"Matricea zice: Rând {r}, Coloană {c} -> {valoare} ({tip})")
        
        # Verificăm și vecinii (poate punctul a căzut fix lângă drum)
        zona = matrice[r-2:r+3, c-2:c+3]
        print(f"\nVecinătatea (5x5 pixeli):\n{zona}")
    else:
        print("Punctul este în afara hărții regiunii Nord-Est!")