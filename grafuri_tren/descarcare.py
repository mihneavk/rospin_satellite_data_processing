import osmnx as ox
import rasterio
from rasterio import features
import numpy as np

# Setări OSMnx
ox.settings.log_console = True
ox.settings.use_cache = True

# Fișiere
# Mergem un folder sus (..) apoi intrăm în 'grafuri'
fisier_sursa_drumuri = "../grafuri/matrice_drumuri_10m.tif" # Îl folosim ca șablon
fisier_output_rail = "matrice_cai_ferate_10m.tif"

# 1. Definim zona (aceleași județe)
queries = [
    {"county": "Suceava", "country": "Romania"},
    {"county": "Botoșani", "country": "Romania"},
    {"county": "Neamț", "country": "Romania"},
    {"county": "Iași", "country": "Romania"},
    {"county": "Bacău", "country": "Romania"},
    {"county": "Vaslui", "country": "Romania"}
]

print("--- 1. Obținem conturul zonei (Poligoanele) ---")
try:
    gdf_judete = ox.geocode_to_gdf(queries)
    zona_totala = gdf_judete.unary_union
    print("Zona definită cu succes.")
except Exception as e:
    print(f"Eroare la geocodare: {e}")
    exit()

print("--- 2. Descărcăm rețeaua de Căi Ferate ---")
# Folosim un filtru personalizat. 
# '["railway"~"rail"]' înseamnă: caută orice etichetă care conține cuvântul "rail"
# Asta include: rail (standard), light_rail, narrow_gauge (mocăniță).
# Exclude: tramvaie urbane (de obicei), metrou.
print("Descărcăm datele (poate dura puțin)...")
G_rail = ox.graph_from_polygon(
    zona_totala, 
    custom_filter='["railway"~"rail"]', 
    simplify=True
)

if len(G_rail.nodes) == 0:
    print("EROARE: Nu s-au găsit căi ferate! Verifică filtrele.")
    exit()

print(f"Am găsit {len(G_rail.edges)} segmente de cale ferată.")

print("--- 3. Proiectăm în metri (UTM) ---")
G_rail_proj = ox.project_graph(G_rail)
# Extragem doar liniile
gdf_rail_edges = ox.graph_to_gdfs(G_rail_proj, nodes=False)

print("--- 4. Pregătim Rasterizarea (Folosind șablonul drumurilor) ---")

# Deschidem harta drumurilor doar pentru a-i fura dimensiunile și coordonatele
with rasterio.open(fisier_sursa_drumuri) as src:
    height = src.height
    width = src.width
    transform_sablon = src.transform
    crs_sablon = src.crs
    print(f"Dimensiuni preluate: {width}x{height}")

# Aplicăm un buffer (grosime) șinelor
# O cale ferată e îngustă, dar punem 3-4 metri buffer ca să fim siguri că atingem pixelii de 10m
print("Aplicăm grosime șinelor...")
shapes_rail = ((geom, 1) for geom in gdf_rail_edges.geometry.buffer(5))

print("Generăm matricea...")
rail_matrix = features.rasterize(
    shapes=shapes_rail,
    out_shape=(height, width),
    transform=transform_sablon, # Folosim exact transformarea de la drumuri!
    fill=0,
    dtype=np.uint8
)

# Statistici simple
nr_pixeli_rail = np.count_nonzero(rail_matrix)
print(f"Total pixeli cale ferată: {nr_pixeli_rail:,}")

print("--- 5. Salvăm matricea Căilor Ferate ---")
with rasterio.open(
    fisier_output_rail, 'w', driver='GTiff',
    height=height, width=width,
    count=1, dtype=str(rail_matrix.dtype),
    crs=crs_sablon,
    transform=transform_sablon,
    compress='lzw'
) as dst:
    dst.write(rail_matrix, 1)

print(f"Succes! Fișierul '{fisier_output_rail}' a fost creat.")