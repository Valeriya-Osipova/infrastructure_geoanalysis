import folium
import geopandas as gpd
from pathlib import Path

# --------------------
# Пути
# --------------------
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

WALK_EDGES = DATA_DIR / "walk_graph" / "walk_edges.geojson"
DRIVE_EDGES = DATA_DIR / "drive_graph" / "drive_edges.geojson"
FINAL_AREAS = DATA_DIR / "final_areas.geojson"

OUTPUT_HTML = Path(__file__).parent / "all_visualize.html"

# --------------------
# Загрузка данных
# --------------------
print("Загружаем данные...")

walk_edges = gpd.read_file(WALK_EDGES)
drive_edges = gpd.read_file(DRIVE_EDGES)
final_areas = gpd.read_file(FINAL_AREAS)

# CRS
walk_edges = walk_edges.to_crs(4326)
drive_edges = drive_edges.to_crs(4326)
final_areas = final_areas.to_crs(4326)

# --------------------
# КРИТИЧЕСКИ ВАЖНО:
# оставляем только геометрию
# --------------------
walk_edges = walk_edges[["geometry"]]
drive_edges = drive_edges[["geometry"]]

# --------------------
# Центр карты
# --------------------
center_geom = final_areas.geometry.union_all().centroid

m = folium.Map(
    location=[center_geom.y, center_geom.x],
    zoom_start=13,
    tiles="cartodbpositron"
)

# --------------------
# Пешеходный граф
# --------------------
folium.GeoJson(
    walk_edges.__geo_interface__,
    name="Пешеходный граф",
    style_function=lambda x: {
        "color": "#2b83ba",
        "weight": 1,
        "opacity": 0.6,
    },
).add_to(m)

# --------------------
# Автомобильный граф
# --------------------
folium.GeoJson(
    drive_edges.__geo_interface__,
    name="Автомобильный граф",
    style_function=lambda x: {
        "color": "#d7191c",
        "weight": 1,
        "opacity": 0.6,
    },
).add_to(m)

# --------------------
# Изохронные зоны
# --------------------
folium.GeoJson(
    final_areas.__geo_interface__,
    name="Изохронные зоны доступности",
    style_function=lambda x: {
        "fillColor": "#1a9641",
        "color": "#1a9641",
        "weight": 2,
        "fillOpacity": 0.35,
    },
).add_to(m)

# --------------------
# Управление слоями
# --------------------
folium.LayerControl(collapsed=False).add_to(m)

# --------------------
# Сохранение
# --------------------
m.save(OUTPUT_HTML)

print(f"Готово. HTML сохранён: {OUTPUT_HTML}")
