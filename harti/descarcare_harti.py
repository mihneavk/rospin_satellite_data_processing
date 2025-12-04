import os
import zipfile
import rasterio
import numpy as np
from pathlib import Path
from shapely.geometry import box
import rasterio.mask
import osmnx as ox
import warnings
from rasterio.warp import reproject, Resampling

# Ignorăm avertismentele pentru un output curat
warnings.filterwarnings("ignore")

# --- CONFIGURARE ---
TEMPLATE_FILE = "../grafuri/matrice_distanta_drum.tif" 
TEMP_DIR = Path("./tmp")
FOLDER_VEGETATIE = "CLMS_CLCplus_RASTER_2018_010m_eu_03035_V1_1"

# --- 1. DEFINIM ZONA DE LUCRU ---
JUDETE_TARGET = [
    {"county": "Suceava", "country": "Romania"},
    {"county": "Botoșani", "country": "Romania"},
    {"county": "Iași", "country": "Romania"},
    {"county": "Neamț", "country": "Romania"},
    {"county": "Bacău", "country": "Romania"},
    {"county": "Vaslui", "country": "Romania"}
]

# --- 2. FUNCȚII UTILITARE ---

def unzip_all(folder):
    """Dezarhivează fișierele .zip."""
    p = Path(folder)
    for file in p.glob("*.zip"):
        target_dir = p / file.stem
        if not target_dir.exists():
            print(f"Dezarhivez: {file.name}...")
            try:
                with zipfile.ZipFile(file, 'r') as zip_ref:
                    zip_ref.extractall(folder)
            except zipfile.BadZipFile:
                 print(f"ATENȚIE: Fișier ZIP corupt: {file.name}")
        else:
            print(f"Arhiva {file.name} pare deja dezarhivată.")

def maskTheMap(matrice_valori):
    """Transformă valorile originale în scoruri militare."""
    mapping = {
        1: -1,   # Clădiri
        2: 5,    # Pădure
        3: 5,    # Pădure
        4: 5,    # Pădure
        5: 7,    # Câmp
        6: 7,    # Câmp
        8: 3,    # Tufișuri
        9: 3,    # Zonă deschisă
        10: 2,   # Apă
        11: 2    # Zone umede
    }
    flavoured = np.copy(matrice_valori).astype(np.int8)
    flavoured[matrice_valori >= 254] = 0
    for orig, new in mapping.items():
        flavoured[matrice_valori == orig] = new
    return flavoured

def process_and_align_matrix(source_folder_name, output_filename, template_path, target_geometry):
    """Căutare recursivă, aliniere și mascare."""
    source_folder = TEMP_DIR / source_folder_name
    
    # --- FIX: Folosim rglob pentru a căuta RECURSIV în subfoldere ---
    tif_files = list(source_folder.rglob("*.tif"))
    
    if not tif_files:
        print(f"EROARE CRITICĂ: Nu găsesc niciun fișier .tif în: {source_folder} (sau subfolderele sale)")
        # Listăm ce există ca să vedem structura
        print("Conținutul găsit:")
        for f in source_folder.rglob("*"):
            print(f" - {f.name}")
        return
    
    # Luăm primul tif găsit (de obicei cel mai mare dacă sunt mai multe, dar aici sperăm că e unul principal)
    # Uneori arhivele au tif-uri mici de 'preview'. Îl căutăm pe cel mai mare.
    source_path = max(tif_files, key=lambda p: p.stat().st_size)
    print(f"Sursa detectată: {source_path.name} (Cale: {source_path})")

    try:
        # 1. Deschide ȘABLONUL
        with rasterio.open(template_path) as template_ds:
            profile_sablon = template_ds.profile.copy()
            template_bounds = box(*template_ds.bounds)
            dst_crs = template_ds.crs
            dst_transform = template_ds.transform
            dst_height = template_ds.height
            dst_width = template_ds.width
            
            print(f"Aliniere la șablon: {dst_width}x{dst_height} pixeli")

            # 2. Deschide Harta Satelit
            with rasterio.open(source_path) as source_ds:
                
                # --- PAS A: ALINIERE (REPROJECT) ---
                # Folosim reproject direct pe array-ul destinație, e mai sigur decât mask+crop
                # când CRS-urile diferă sau structura e complexă.
                
                print("1. Reproiectăm și aliniem harta satelit...")
                # Creăm matricea goală aliniată
                destination_array = np.zeros((dst_height, dst_width), dtype=np.uint8)
                
                reproject(
                    source=rasterio.band(source_ds, 1),
                    destination=destination_array,
                    src_transform=source_ds.transform,
                    src_crs=source_ds.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest,
                    dst_nodata=0
                )

                # --- PAS B: SCORARE ---
                print("2. Transformăm valorile...")
                matrice_scorata = maskTheMap(destination_array)

                # --- PAS C: MASCARE GEOGRAFICĂ ---
                print("3. Eliminăm zonele din afara județelor...")
                
                # Scriem în memorie pentru a aplica masca vectorială
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
                            shapes=[target_geometry],
                            crop=False, 
                            filled=True, 
                            nodata=0 
                        )

            # 3. Salvare
            profile_sablon.update(dtype=rasterio.int8, count=1, nodata=0, compress='lzw')

            print(f"4. Salvăm rezultatul în '{output_filename}'...")
            with rasterio.open(output_filename, 'w', **profile_sablon) as dst:
                dst.write(final_matrix[0], 1)

            print(f"\nSUCCES! Dimensiuni: {final_matrix[0].shape}")
            
    except Exception as e:
        print(f"Eroare la procesare: {e}")

# --- 3. EXECUTIA PRINCIPALĂ ---
if __name__ == "__main__":
    
    if not Path(TEMPLATE_FILE).exists():
        print(f"FATAL: Nu găsesc șablonul '{TEMPLATE_FILE}'.")
        exit()

    print("--- Pasul 1: Geometria județelor ---")
    try:
        gdf_judete = ox.geocode_to_gdf(JUDETE_TARGET)
        zona_totala_poligon = gdf_judete.unary_union 
    except Exception as e:
        print(f"Eroare: {e}")
        exit()

    print("--- Pasul 2: Verificare date ---")
    unzip_all(TEMP_DIR)

    print("--- Pasul 3: Procesare Finală ---")
    process_and_align_matrix(
        FOLDER_VEGETATIE, 
        "matrice_satelit_finala.tif",
        TEMPLATE_FILE,
        zona_totala_poligon
    )
    print("\nScript finalizat.")