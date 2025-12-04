import os
import zipfile
import rasterio
import rasterio.warp
from rasterio.windows import Window
from pathlib import Path

# --- Setările tale ---

# 1. Folderul de bază unde se află arhiva ZIP
base_folder = "./tmp"

# 2. Numele arhivei ZIP
zip_filename = "CLMS_CLCPLUS_RAS_S2023_R10m_E54N27_03035_V01_R00.zip"

# 3. Coordonatele de verificat (am extras numerele din textul tău)
coordinates_to_check = [
    {'lat': 46.6969, 'lon': 25.5212},  # "46.6969N, 25.5212E"
    {'lat': 46.6961, 'lon': 25.5189},  # "46.6961N, 25.5189E"
    {'lat': 46.6958, 'lon': 25.5201}   # "46.6958N, 25.5201E"
]

# --- Sfârșitul setărilor ---


def get_pixel_value_from_open_dataset(dataset, lat, lon, input_crs="EPSG:4326"):
    """
    Funcție ajutătoare care preia valoarea unui pixel dintr-un set de date 
    rasterio *deja deschis*.
    """
    try:
        # 1. Obține CRS-ul rasterului din setul de date
        raster_crs = dataset.crs
        
        # 2. Transformă coordonatele Lat/Lon (EPSG:4326) în CRS-ul rasterului
        transformed_coords = rasterio.warp.transform(
            input_crs,
            raster_crs,
            [lon],  # Lista de X (longitudini)
            [lat]   # Lista de Y (latitudini)
        )
        
        x_coord = transformed_coords[0][0]
        y_coord = transformed_coords[1][0]

        # 3. Găsește indexul (rândul și coloana) pixelului
        row, col = dataset.index(x_coord, y_coord)

        # 4. Citește valoarea doar pentru acel pixel (fereastră 1x1)
        window = Window(col, row, 1, 1)
        pixel_value = dataset.read(1, window=window)[0][0]
        
        return pixel_value
        
    except Exception as e:
        # Prinde erori, de ex. dacă coordonatele sunt în afara hărții
        return f"EROARE: {e}"


def main_process(base_dir, zip_name, coords_list):
    """
    Funcția principală care orchestrează dezarhivarea și verificarea.
    """
    try:
        # --- Pasul 1: Definirea Căilor ---
        
        # Asigură-te că folosim căi absolute pentru siguranță
        base_dir_path = Path(base_dir).resolve()
        zip_path = base_dir_path / zip_name
        
        # Numele folderului de ieșire va fi numele arhivei fără ".zip"
        extract_folder_name = zip_path.stem
        extract_path = base_dir_path / extract_folder_name
        
        # Numele fișierului .tif va fi același cu al folderului
        tif_filename = extract_folder_name + ".tif"
        tif_path = extract_path / tif_filename

        # --- Pasul 2: Dezarhivarea ---
        if not extract_path.exists():
            print(f"Folderul de extras nu există. Se dezarhivează {zip_path}...")
            if not zip_path.exists():
                print(f"EROARE CRITICĂ: Arhiva ZIP nu a fost găsită la {zip_path}")
                return

            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_path)
            print(f"Dezarhivare finalizată în: {extract_path}")
        else:
            print(f"Folderul {extract_path} există deja. Se sare peste dezarhivare.")

        # --- Pasul 3: Verificarea fișierului TIF ---
        if not tif_path.exists():
            print(f"EROARE CRITICĂ: Fișierul .TIF așteptat nu a fost găsit la {tif_path}")
            print("Verifică dacă arhiva ZIP conține un .tif cu același nume.")
            return

        # --- Pasul 4: Citirea Rasterului și Verificarea Coordonatelor ---
        print(f"\nSe încarcă harta: {tif_path}")
        with rasterio.open(tif_path) as dataset:
            print("Harta încărcată cu succes. Se verifică coordonatele:")
            
            for i, coord in enumerate(coords_list):
                lat = coord['lat']
                lon = coord['lon']
                
                value = get_pixel_value_from_open_dataset(dataset, lat, lon)
                
                print(f"  {i+1}. La (Lat: {lat}, Lon: {lon}) -> Valoarea pixelului = {value}")

    except Exception as e:
        print(f"A apărut o eroare generală în proces: {e}")


# --- Punctul de intrare în script ---
if __name__ == "__main__":
    main_process(base_folder, zip_filename, coordinates_to_check)