import rasterio
import numpy as np
from pathlib import Path
from shapely.geometry import box
import rasterio.mask
import osmnx as ox
import warnings
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds
import geopandas as gpd # Avem nevoie de asta pentru reproiectare

warnings.filterwarnings("ignore")

# --- CONFIGURARE ---
TEMPLATE_FILE = "../grafuri/matrice_distanta_drum.tif" 
TEMP_DIR = Path("./tmp")
# Numele folderului sursă
FOLDER_VEGETATIE = "CLMS_CLCplus_RASTER_2018_010m_eu_03035_V1_1"

# --- 1. DEFINIRE ZONA ---
JUDETE_TARGET = [
    {"county": "Suceava", "country": "Romania"},
    {"county": "Botoșani", "country": "Romania"},
    {"county": "Iași", "country": "Romania"},
    {"county": "Neamț", "country": "Romania"},
    {"county": "Bacău", "country": "Romania"},
    {"county": "Vaslui", "country": "Romania"}
]

def maskTheMap(matrice_valori):
    """Transformă valorile originale în scoruri militare."""
    # Mapping simplificat pentru CLC+
    mapping = {
        1: -1,   # Urban
        2: 5,    # Pădure
        3: 5,    # Pădure
        4: 5,    # Pădure
        5: 7,    # Câmp
        6: 7,    # Câmp
        8: 3,    # Tufișuri
        9: 3,    # Zonă deschisă
        10: 2,   # Apă
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
    source_folder = TEMP_DIR / source_folder_name
    tif_files = list(source_folder.rglob("*.tif"))
    
    if not tif_files:
        print("EROARE: Nu găsesc fișierul .tif sursă.")
        return
    
    source_path = max(tif_files, key=lambda p: p.stat().st_size)
    print(f"\nSursa Detectată: {source_path.name}")

    try:
        # 1. Analizăm ȘABLONUL (Ținta - UTM)
        with rasterio.open(template_path) as tmpl:
            dst_crs = tmpl.crs
            dst_transform = tmpl.transform
            dst_width = tmpl.width
            dst_height = tmpl.height
            dst_bounds = tmpl.bounds
            profile_out = tmpl.profile.copy()
            print(f"Ținta (Moldova UTM): {dst_width}x{dst_height}")

            # --- FIX: REPROIECTĂM POLIGONUL DE TĂIERE ---
            print("Convertim forma județelor din GPS (WGS84) în Metri (UTM)...")
            # Creăm un GeoSeries temporar pentru a face conversia matematică
            poly_series = gpd.GeoSeries([target_geometry_wgs84], crs="EPSG:4326")
            poly_utm = poly_series.to_crs(dst_crs)
            # Extragem geometria convertită
            target_geometry_utm = poly_utm.geometry[0]


            # 2. Analizăm SURSA (Europa LAEA)
            with rasterio.open(source_path) as src:
                # Calculăm fereastra
                left, bottom, right, top = transform_bounds(dst_crs, src.crs, *dst_bounds)
                margin = 1000 
                window = from_bounds(left - margin, bottom - margin, right + margin, top + margin, transform=src.transform)
                
                # 3. CITIM
                print("Citesc datele...")
                source_data = src.read(1, window=window)
                source_transform = src.window_transform(window)
                
                if source_data.max() == 0:
                    print("❌ EROARE: Zona citită este goală!")
                    return

                # 4. REPROIECTĂM (LAEA -> UTM)
                print("Reproiectez la grila finală...")
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
                
                # 5. SCORARE
                print("Aplic scorurile militare...")
                matrice_scorata = maskTheMap(destination_data)
                
                # VERIFICARE INTERMEDIARĂ
                valori_inainte_de_masca = np.unique(matrice_scorata)
                print(f"   -> Valori prezente: {valori_inainte_de_masca}")

                # 6. MASCARE (Acum folosim geometria UTM!)
                print("Mascăm conturul județelor (Acum coordonatele se potrivesc!)...")
                
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
                            shapes=[target_geometry_utm], # <--- FOLOSIM VARIANTA UTM
                            crop=False, 
                            filled=True, 
                            nodata=0 
                        )
                
                # Verificăm dacă a mai rămas ceva după mascare
                if np.max(final_matrix) == 0:
                     print("❌ EROARE: Totul a dispărut după mascare! Verifică conversia coordonatelor.")
                else:
                     print("✅ Mascarea a reușit! Avem date în interiorul județelor.")

            # 7. SALVARE
            profile_out.update(dtype=rasterio.int8, count=1, nodata=0, compress='lzw')
            
            print(f"Salvez rezultatul în '{output_filename}'...")
            with rasterio.open(output_filename, 'w', **profile_out) as dst:
                dst.write(final_matrix[0], 1)

            print(f"SUCCES!")

    except Exception as e:
        print(f"EROARE CRITICĂ: {e}")
        import traceback
        traceback.print_exc()

# --- EXECUȚIE ---
if __name__ == "__main__":
    
    if not Path(TEMPLATE_FILE).exists():
        print(f"FATAL: Nu găsesc șablonul '{TEMPLATE_FILE}'.")
        exit()

    print("--- Pasul 1: Geometria județelor ---")
    gdf_judete = ox.geocode_to_gdf(JUDETE_TARGET)
    zona_totala_poligon_wgs84 = gdf_judete.unary_union 

    print("--- Pasul 2: Extracție Chirurgicală ---")
    surgical_extraction(
        FOLDER_VEGETATIE, 
        "matrice_satelit_finala.tif",
        TEMPLATE_FILE,
        zona_totala_poligon_wgs84
    )