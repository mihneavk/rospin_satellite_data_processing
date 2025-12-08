import osmnx as ox
import matplotlib.pyplot as plt
import sys



if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Configurăm log-urile
ox.settings.log_console = True
ox.settings.use_cache = True

# Definim lista folosind DICTIONARE (Căutare structurată)
# Asta elimină confuzia între Oraș și Județ
queries = [
    {"county": "Suceava", "country": "Romania"},
    {"county": "Botoșani", "country": "Romania"}, # Cu diacritice e mai sigur în OSM
    {"county": "Neamț", "country": "Romania"},
    {"county": "Iași", "country": "Romania"},
    {"county": "Bacău", "country": "Romania"},
    {"county": "Vaslui", "country": "Romania"}
]

print("--- 1. Căutăm limitele administrative (Poligoanele)... ---")

try:
    # Îi dăm lista de dicționare. OSMNX va face request pentru fiecare.
    gdf_judete = ox.geocode_to_gdf(queries)
    print("Victorie! Am găsit toate cele 6 județe.")
    
    # Le unim într-o singură formă mare
    zona_totala = gdf_judete.unary_union
    print("Am unit județele într-o singură regiune (Nord-Est).")

except Exception as e:
    print(f"Eroare critică la găsirea județelor: {e}")
    # Putem vedea exact care a eșuat dacă rulam pas cu pas, dar de obicei structura asta merge.
    exit()

print("--- 2. Începe descărcarea rețelei de drumuri... ---")
print("Notă: Aceasta este partea grea. Poate dura 5-10 minute pentru toată Moldova.")

# Descărcăm doar drumurile majore și secundare pentru a salva memorie și timp?
# 'drive' ia tot ce e carosabil. E ok pentru început.
try:
    G = ox.graph_from_polygon(zona_totala, network_type='drive', simplify=True)
    
    print(f"Succes! Rețea descărcată: {len(G.nodes)} noduri și {len(G.edges)} muchii.")

    # 3. Salvarea
    print("Salvez fișierul pe disk...")
    ox.save_graphml(G, "drumuri_nord_est.graphml")
    print("GATA! Fișierul 'drumuri_nord_est.graphml' a fost creat.")

except Exception as e:
    print(f"Eroare la descărcarea grafului: {e}")