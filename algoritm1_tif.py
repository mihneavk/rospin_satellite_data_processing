import rasterio
import numpy as np
import heapq
import os
import json
import argparse
from pathlib import Path
from rasterio.warp import transform_bounds, transform

# --- CONFIGURARE ---
INPUT_FILE = "MATRICE_SCOR_FINAL.tif"
OUTPUT_JSON_FILE = "rezultate_baze_gps.json"

def primele100ElementeMaxime(mat):
    """Găsește cele mai mari 100 de valori din matricea dată."""
    matrice_aplatizata = mat.ravel()
    k = min(100, len(matrice_aplatizata))
    if k == 0: return []
    
    indici_maximi = np.argpartition(-matrice_aplatizata, k-1)[:k]
    maxime = matrice_aplatizata[indici_maximi]
    coordonate = np.unravel_index(indici_maximi, mat.shape)
    
    elemente_maxime = []
    for val, r, c in zip(maxime, coordonate[0], coordonate[1]):
        if val > 0:
            elemente_maxime.append((val, r, c))
            
    elemente_maxime.sort(key=lambda x: x[0], reverse=True)
    return elemente_maxime

def selectareCuRespectareDistanta(baze, patrate, elemente_maxime):
    selectate = []
    distanta_minima = int(np.sqrt(patrate)) + 2 

    for val, i, j in elemente_maxime:
        bagam = True
        for _, si, sj in selectate:
            if abs(i - si) < distanta_minima and abs(j - sj) < distanta_minima:
                bagam = False
                break
        if bagam:
            selectate.append((val, i, j))
            if len(selectate) == baze:
                break
    return selectate

def generareOConfiguratie(element_curent, patrate, mat):
    scor_start, start_i, start_j = element_curent
    linii, coloane = mat.shape

    max_heap = [(-int(mat[start_i, start_j]), start_i, start_j)]
    vizitate = set([(start_i, start_j)])
    configuratie = []

    while len(configuratie) < patrate and max_heap:
        val_neg, r, c = heapq.heappop(max_heap)
        val = -val_neg
        
        if val <= 0: continue
            
        configuratie.append((val, r, c))

        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < linii and 0 <= nc < coloane and (nr, nc) not in vizitate:
                vizitate.add((nr, nc))
                heapq.heappush(max_heap, (-int(mat[nr, nc]), nr, nc))

    return configuratie

def generareConfiguratii(selectate, patrate, mat, baze):
    toate_configuratiile = []
    for element in selectate:
        configuratie = generareOConfiguratie(element, patrate, mat)
        if len(configuratie) == patrate:
            suma_totala = sum(celula[0] for celula in configuratie)
            toate_configuratiile.append((suma_totala, configuratie))

    toate_configuratiile.sort(key=lambda x: x[0], reverse=True)
    return toate_configuratiile[:baze]

def pixel_to_gps(src, row, col):
    """Transformă indecșii matricii (Row, Col) în coordonate GPS (Lat, Lon)."""
    # 1. Obținem coordonatele native ale hărții (UTM)
    x_utm, y_utm = src.xy(row, col)
    
    # 2. Transformăm UTM -> WGS84 (Lat/Lon)
    # transform returnează liste de coordonate, noi luăm primul element
    lon, lat = transform(src.crs, "EPSG:4326", [x_utm], [y_utm])
    
    return lat[0], lon[0]

def structurarePentruJSON(configuratii, src, offset_row, offset_col):
    """
    Construiește JSON-ul final convertind pixelii înapoi în Lat/Lon.
    """
    if not configuratii: return []

    rezultat = []
    baze = len(configuratii)
    start, end = 30, 80
    pas_variatie = (end - start) / max(baze, 1)

    for k, (suma, configuratie) in enumerate(configuratii):
        valoare_gb = int(min(255, round(start + k * pas_variatie)))
        gb_hex = f"{valoare_gb:02X}"
        culoare_hex = f"#FF{gb_hex}{gb_hex}"

        lista_celule = []
        for scor, r_local, c_local in configuratie:
            # Calculăm indexul global
            r_global = r_local + offset_row
            c_global = c_local + offset_col
            
            # Convertim în GPS
            lat, lon = pixel_to_gps(src, r_global, c_global)
            
            lista_celule.append({
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "scor": int(scor)
            })

        baza_structurata = {
            "id": k + 1,
            "scor_total": int(suma),
            "culoare": culoare_hex,
            "celule": lista_celule
        }
        rezultat.append(baza_structurata)

    return rezultat

def afisare_si_salvare_rezultate(rezultate_json):
    if not rezultate_json:
        print("❌ Nu au fost găsite baze valide.")
        with open(OUTPUT_JSON_FILE, "w") as f: json.dump([], f)
        return

    print("\n" + "="*80)
    print("🏆 CLASAMENT BAZE OPTIME (Coordonate GPS)")
    print("="*80)
    print(f"{'ID':<4} | {'Scor':<6} | {'Start (Lat, Lon)':<25} | {'Celule'}")
    print("-" * 55)

    for baza in rezultate_json:
        start = baza['celule'][0]
        start_str = f"{start['lat']:.5f}, {start['lon']:.5f}"
        print(f"{baza['id']:<4} | {baza['scor_total']:<6} | {start_str:<25} | {len(baza['celule'])}")

    try:
        with open(OUTPUT_JSON_FILE, "w") as f:
            json.dump(rezultate_json, f, indent=4)
        print(f"\n✅ JSON salvat: '{OUTPUT_JSON_FILE}'")
    except Exception as e:
        print(f"❌ Eroare salvare JSON: {e}")

def algoritm_baze_gps(lat1, lon1, lat2, lon2, patrate, nr_baze):
    if not Path(INPUT_FILE).exists():
        print(f"EROARE: Fișierul '{INPUT_FILE}' lipsește.")
        return

    print(f"--- Căutare Baze în zona: {lat1}, {lon1} <-> {lat2}, {lon2} ---")

    with rasterio.open(INPUT_FILE) as src:
        # 1. Transformăm BBox-ul GPS (Lat/Lon) în Indecși Matrice (Row/Col)
        south, north = min(lat1, lat2), max(lat1, lat2)
        west, east = min(lon1, lon2), max(lon1, lon2)
        
        try:
            # Lat/Lon -> UTM
            left, bottom, right, top = transform_bounds("EPSG:4326", src.crs, west, south, east, north)
            
            # UTM -> Pixeli (Window)
            window = rasterio.windows.from_bounds(left, bottom, right, top, transform=src.transform)
            
            # Rotunjim și convertim la int
            window = window.round_offsets().round_lengths()
            col_off, row_off = int(window.col_off), int(window.row_off)
            width, height = int(window.width), int(window.height)
            
        except Exception as e:
            print(f"Eroare conversie coordonate: {e}")
            return

        # 2. Citim datele
        print(f"Analizez o zonă de {width}x{height} pixeli...")
        
        try:
            mat_local = src.read(1, window=window)
        except Exception:
            print("Zona selectată este în afara hărții.")
            return

        if mat_local.size == 0 or np.max(mat_local) <= 0:
            print("Zona este goală sau neconstruibilă (doar 0 sau -1).")
            afisare_si_salvare_rezultate([])
            return

        # 3. Rulăm Algoritmul
        elemente_maxime = primele100ElementeMaxime(mat_local)
        
        if not elemente_maxime:
            print("Nu s-au găsit puncte valide.")
            afisare_si_salvare_rezultate([])
            return

        selectate = selectareCuRespectareDistanta(nr_baze, patrate, elemente_maxime)
        configuratii = generareConfiguratii(selectate, patrate, mat_local, nr_baze)
        
        # 4. Generăm rezultatul cu conversie inversă (Pixel -> GPS)
        # Pasăm 'src' și offset-urile ferestrei pentru a putea calcula coordonatele globale
        rezultat_final = structurarePentruJSON(configuratii, src, row_off, col_off)

        afisare_si_salvare_rezultate(rezultat_final)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Găsește baze militare folosind coordonate GPS.")
    
    parser.add_argument("lat1", type=float, help="Latitudine punct 1")
    parser.add_argument("lon1", type=float, help="Longitudine punct 1")
    parser.add_argument("lat2", type=float, help="Latitudine punct 2")
    parser.add_argument("lon2", type=float, help="Longitudine punct 2")
    parser.add_argument("pixeli_baze", type=int, help="Mărimea bazei (nr pixeli)")
    parser.add_argument("nr_baze", type=int, help="Numărul de baze")

    args = parser.parse_args()

    algoritm_baze_gps(args.lat1, args.lon1, args.lat2, args.lon2, args.pixeli_baze, args.nr_baze)