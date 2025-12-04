import os
import zipfile
import rasterio
import numpy as np
from pathlib import Path
from shapely.geometry import box
import rasterio.mask
import osmnx as ox
import warnings
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds
import geopandas as gpd
from hda import Client, Configuration

# Ignorăm avertismentele inutile
warnings.filterwarnings("ignore")

# ==========================================
#               CONFIGURARE
# ==========================================

# 1. Credențiale HDA (Copernicus)
USERNAME_HDA = "logimap"
PASSWORD_HDA = "dvga!vgdva2@A"

# 2. Căi Fișiere
# Șablonul este esențial pentru aliniere!
TEMPLATE_FILE = "../grafuri/matrice_distanta_drum.tif" 
TEMP_DIR = Path("./tmp")
OUTPUT_FILE = "matrice_satelit_finala.tif"

# 3. Numele setului de date (Dataset ID)
DATASET_ID = "EO:EEA:DAT:CLC-PLUS"
YEAR = "2018"
# Numele folderului rezultat după dezarhivare (pentru a ști ce căutăm)
TARGET_FOLDER_NAME = "CLMS_CLCplus_RASTER_2018_010m_eu_03035_V1_1"

# 4. Zona de Interes
JUDETE_TARGET = [
    {"county": "Suceava", "country": "Romania"},
    {"county": "Botoșani", "country": "Romania"},
    {"county": "Iași", "country": "Romania"},
    {"county": "Neamț", "country": "Romania"},
    {"county": "Bacău", "country": "Romania"},
    {"county": "Vaslui", "country": "Romania"}
]

# ==========================================
#           FUNCȚII UTILITARE
# ==========================================

def unzip_all(folder):
    """Dezarhivează fișierele .zip din folderul temporar."""
    p = Path(folder)
    for file in p.glob("*.zip"):
        # Verificăm dacă pare deja extras
        target_dir = p / file.stem
        # Sau verificăm numele specific al folderului țintă
        specific_target = p / TARGET_FOLDER_NAME
        
        if target_dir.exists() or specific_target.exists():
            print(f"Arhiva {file.name} pare deja dezarhivată.")
            continue
            
        print(f"Dezarhivez: {file.name}...")
        try:
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(folder)
        except zipfile.BadZipFile:
             print(f"ATENȚIE: Fișier ZIP corupt: {file.name}")

def downloadMaps(dataset_id, bbox, year):
    """Descarcă harta folosind API-ul HDA."""
    print(f"\n--- Verificare Descărcare: {dataset_id} ---")
    
    # Verificăm dacă datele există deja ca să nu descărcăm 8GB inutil
    expected_path = TEMP_DIR / TARGET_FOLDER_NAME
    if expected_path.exists():
        print(f"Folderul '{TARGET_FOLDER_NAME}' există deja. Sărim peste descărcare.")
        return

    print("Inițializez clientul HDA...")
    try:
        conf = Configuration(user=USERNAME_HDA, password=PASSWORD_HDA)
        hda_client = Client(config=conf)
        
        query = {
            "dataset_id": dataset_id,
            "bbox": bbox,
            "productType": "Raster Layer",
            "resolution": "10m",
            "year": year,
            "itemsPerPage": 200,
            "startIndex": 0
        }
        
        print("Caut fișierul pe server...")
        matches = hda_client.search(query)
        print(f"Găsit! Începe descărcarea în {TEMP_DIR}...")
        matches.download(download_dir=TEMP_DIR)
        
    except Exception as e:
        print(f"Eroare la descărcare HDA: {e}")

def maskTheMap(matrice_valori):
    """Transformă valorile originale în scoruri militare."""
    # Mapping CLC+
    mapping = {
        1: -1,   # Clădiri (Obstacol)
        2: 5,    # Pădure (Ascunzătoare)
        3: 5,    # Pădure
        4: 5,    # Pădure
        5: 7,    # Câmp (Vizibilitate)
        6: 7,    # Câmp
        8: 3,    # Tufișuri
        9: 3,    # Zonă deschisă
        10: 2,   # Apă (Obstacol)
        11: 2,   # Apă
        255: 0,  # NoData
        0: 0
    }
    
    flavoured = np.copy(matrice_valori).astype(np.int8)
    flavoured[matrice_valori >= 254] = 0
    
    for orig, new in mapping.items():
        flavoured[matrice_valori == orig] = new
        
    return flavoured

def surgical_extraction(source_folder_name, output_filename, template_path, target_geometry_wgs84):
    """Extrage, Aliniază, Reproiectează și Maschează datele."""
    source_folder = TEMP_DIR / source_folder_name
    
    # Căutăm recursiv fișierul TIF
    tif_files = list(source_folder.rglob("*.tif"))
    
    if not tif_files:
        print(f"EROARE CRITICĂ: Nu găsesc niciun fișier .tif în {source_folder}")
        return
    
    # Alegem cel mai mare fișier (harta propriu-zisă)
    source_path = max(tif_files, key=lambda p: p.stat().st_size)
    print(f"\nFișier Sursă Detectat: {source_path.name}")

    try:
        # 1. Analizăm ȘABLONUL (Ținta - UTM)
        with rasterio.open(template_path) as tmpl:
            dst_crs = tmpl.crs
            dst_transform = tmpl.transform
            dst_width = tmpl.width
            dst_height = tmpl.height
            dst_bounds = tmpl.bounds
            profile_out = tmpl.profile.copy()
            print(f"Dimensiuni Țintă (Moldova UTM): {dst_width}x{dst_height}")

            # --- CONVERSIE POLIGON: WGS84 -> UTM ---
            print("Convertim forma județelor în sistem metric...")
            poly_series = gpd.GeoSeries([target_geometry_wgs84], crs="EPSG:4326")
            poly_utm = poly_series.to_crs(dst_crs)
            target_geometry_utm = poly_utm.geometry[0]

            # 2. Analizăm SURSA (Europa LAEA)
            with rasterio.open(source_path) as src:
                # Calculăm fereastra exactă de citire
                left, bottom, right, top = transform_bounds(dst_crs, src.crs, *dst_bounds)
                margin = 2000 # Marjă de siguranță (metri)
                window = from_bounds(left - margin, bottom - margin, right + margin, top + margin, transform=src.transform)
                
                print("Citesc doar zona Moldovei din fișierul gigant...")
                source_data = src.read(1, window=window)
                source_transform = src.window_transform(window)
                
                if source_data.max() == 0:
                    print("❌ EROARE: Zona citită este goală (doar 0)!")
                    return

                # 3. REPROIECTĂM (LAEA -> UTM)
                print("Reproiectez la grila drumurilor...")
                destination_data = np.zeros((dst_height, dst_width), dtype=np.uint8)
                
                reproject(
                    source=source_data,
                    destination=destination_data,
                    src_transform=source_transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest,
                    dst_nodata=0
                )
                
                # 4. SCORARE MILITARĂ
                print("Aplic scorurile tactice...")
                matrice_scorata = maskTheMap(destination_data)
                
                # 5. MASCARE FINALĂ
                print("Decupez exact pe conturul județelor...")
                
                with rasterio.MemoryFile() as memfile:
                    with memfile.open(
                        driver='GTiff',
                        height=dst_height,
                        width=dst_width,
                        count=1,
                        dtype=rasterio.int8,
                        crs=dst_crs,
                        transform=dst_transform
                    ) as dataset_temp:
                        dataset_temp.write(matrice_scorata, 1)
                        
                        final_matrix, _ = rasterio.mask.mask(
                            dataset=dataset_temp,
                            shapes=[target_geometry_utm], # Geometria UTM corectă
                            crop=False, 
                            filled=True, 
                            nodata=0 
                        )

            # 6. SALVARE
            profile_out.update(dtype=rasterio.int8, count=1, nodata=0, compress='lzw')
            
            print(f"Salvez rezultatul în '{output_filename}'...")
            with rasterio.open(output_filename, 'w', **profile_out) as dst:
                dst.write(final_matrix[0], 1)

            print(f"✅ SUCCES! Harta satelitară este gata.")

    except Exception as e:
        print(f"EROARE CRITICĂ: {e}")

# ==========================================
#           EXECUȚIA PRINCIPALĂ
# ==========================================
if __name__ == "__main__":
    
    # 0. Verificare prealabilă
    if not Path(TEMPLATE_FILE).exists():
        print(f"FATAL: Nu găsesc șablonul '{TEMPLATE_FILE}'.")
        print("Rulează mai întâi scriptul pentru drumuri!")
        exit()

    # Creăm folderul tmp
    TEMP_DIR.mkdir(exist_ok=True)

    # 1. Calcul Geometrie Globală
    print("--- Pasul 1: Calcul Geometrie Județe (WGS84) ---")
    try:
        gdf_judete = ox.geocode_to_gdf(JUDETE_TARGET)
        zona_totala_wgs84 = gdf_judete.unary_union
        
        # Extragem Bounding Box-ul pentru download (West, South, East, North)
        bounds = zona_totala_wgs84.bounds
        bbox_list = [bounds[0], bounds[1], bounds[2], bounds[3]]
        print(f"BBox calculat: {bbox_list}")
        
    except Exception as e:
        print(f"Eroare geometrie: {e}")
        exit()

    # 2. Descărcare (Download)
    print("\n--- Pasul 2: Descărcare Date ---")
    downloadMaps(DATASET_ID, bbox_list, YEAR)

    # 3. Dezarhivare
    print("\n--- Pasul 3: Dezarhivare ---")
    unzip_all(TEMP_DIR)

    # 4. Procesare Finală
    print("\n--- Pasul 4: Procesare & Generare Hartă ---")
    surgical_extraction(
        TARGET_FOLDER_NAME, 
        OUTPUT_FILE,
        TEMPLATE_FILE,
        zona_totala_wgs84
    )
    
    print("\nScript complet finalizat.")