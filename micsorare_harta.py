from rasterio.enums import Resampling
import rasterio
import numpy as np
from pathlib import Path


base_folder = "./tmp"
folder_name = "CLMS_CLCPLUS_RAS_S2023_R10m_E54N27_03035_V01_R00"
tif_name = folder_name + ".tif"

# Construim calea completă către fișierul .tif
tif_path = Path(base_folder) / folder_name / tif_name

with rasterio.open(tif_path) as dataset:
    # Calculează noua formă, de 10 ori mai mică
    noua_inaltime = dataset.height // 10
    noua_latime = dataset.width // 10
    
    # Citim datele și le redimensionăm automat
    matrice_preview = dataset.read(
        1,
        out_shape=(noua_inaltime, noua_latime),
        resampling=Resampling.nearest  # Folosim 'nearest' pt date de clasificare
    )
    
    print(f"Forma matricii preview: {matrice_preview.shape}")
    print(matrice_preview)