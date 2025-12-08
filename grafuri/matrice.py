import osmnx as ox
import geopandas as gpd
import rasterio
from rasterio import features
from rasterio.transform import from_origin
import numpy as np
import sys



if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

print("--- 1. Încărcăm graful salvat anterior (poate dura puțin)... ---")
G = ox.load_graphml("drumuri_nord_est.graphml")

print("--- 2. Proiectăm graful în metri (UTM) ---")
# Acest pas este CRITIC. Transformă gradele geografice în metri.
# osmnx detectează automat zona UTM potrivită pentru România (Zona 35N).
G_proj = ox.project_graph(G)

# Extragem doar liniile (drumurile) într-un GeoDataFrame
# nodes=False înseamnă că nu ne interesează intersecțiile ca puncte, ci doar liniile
gdf_edges = ox.graph_to_gdfs(G_proj, nodes=False)

print("--- 3. Calculăm Dreptunghiul (Bounding Box) ---")
minx, miny, maxx, maxy = gdf_edges.total_bounds

print(f"Coordonate Dreptunghi (UTM metri):")
print(f"  Stânga (Vest): {minx:.2f}")
print(f"  Jos (Sud):     {miny:.2f}")
print(f"  Dreapta (Est): {maxx:.2f}")
print(f"  Sus (Nord):    {maxy:.2f}")

# Definim rezoluția
pixel_size = 10  # 10 metri per pixel

# Calculăm dimensiunile matricei (Lățime x Înălțime)
width = int((maxx - minx) / pixel_size) + 1
height = int((maxy - miny) / pixel_size) + 1

print(f"\nDimensiunea Matricei rezultate: {width} x {height} pixeli")
print(f"Total pixeli: {width * height:,}")

print("--- 4. Creăm matricea și 'ardem' drumurile ---")

# Transformarea definește legătura dintre pixelii matricei și coordonatele reale
# from_origin(vest, nord, x_size, y_size)
transform = from_origin(minx, maxy, pixel_size, pixel_size)

# Pentru ca drumul să fie vizibil pe grila de 10m, îi dăm o grosime (buffer).
# Liniile vectoriale au grosime 0. Facem un buffer de 6m (rezultă drum lat de ~12m),
# suficient să atingă cel puțin un pixel de 10m oriunde ar trece.
print("Aplicăm grosime drumurilor (Buffer)...")
shapes = ((geom, 1) for geom in gdf_edges.geometry.buffer(6))

print("Rasterizăm (Generăm matricea 0/1)...")
# Matrice de tip 'uint8' (consumă puțină memorie, valori 0-255)
# fill=0 înseamnă că fundalul e zero
drumuri_matrix = features.rasterize(
    shapes=shapes,
    out_shape=(height, width),
    transform=transform,
    fill=0,
    dtype=np.uint8
)

print("--- 5. Salvăm rezultatul ---")

# Salvăm ca fișier GeoTIFF (imagine standard geospațială)
# Poate fi deschis în QGIS sau reîncărcat în Python ca matrice numpy
nume_fisier = "matrice_drumuri_10m.tif"

with rasterio.open(
    nume_fisier, 'w', driver='GTiff',
    height=height, width=width,
    count=1, dtype=str(drumuri_matrix.dtype),
    crs=gdf_edges.crs,
    transform=transform,
    compress='lzw' # Compresie ca să nu ocupe mult spațiu pe disk
) as dst:
    dst.write(drumuri_matrix, 1)

print(f"Gata! Matricea a fost salvată în '{nume_fisier}'.")
print("Acum ai o matrice unde 1 = drum și 0 = câmp.")