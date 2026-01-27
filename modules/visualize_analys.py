import os
import folium
from shapely.geometry import shape
from accessibility_module import analyze_accessibility
from isochrones_module import build_isochrone
import geopandas as gpd

# ------------------------------------------------------------
# Базовая директория
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------
# Пути к данным
# ------------------------------------------------------------
social_file = os.path.join(BASE_DIR, "../data/social_infrastructure_points.geojson")
SOCIAL_GDF = gpd.read_file(social_file).set_crs(epsg=4326, allow_override=True)

nodes_file = os.path.join(BASE_DIR, "../data/road_big_nodes.geojson")
NODES_GDF = gpd.read_file(nodes_file).set_crs(epsg=4326, allow_override=True)

# ------------------------------------------------------------
# Цвета по типу инфраструктуры
# ------------------------------------------------------------
COLORS = {
    "kindergarten": "orange",
    "school": "blue",
    "college": "purple",
    "hospital": "red",
    "clinic": "red",
}

# Цвета изохрон в зависимости от типа
ISO_COLORS = {
    "kindergarten": "orange",
    "school": "blue",
    "college": "purple",
    "hospital": "red"
}

# ------------------------------------------------------------
# Функция для добавления изохрон на карту
# ------------------------------------------------------------
def add_isochrone_map(m, iso_feature, layer_name, color="blue", fill_opacity=0.2):
    """Добавляем изохронный полигон на карту Folium в отдельный слой"""
    fg = folium.FeatureGroup(name=layer_name, show=True)
    folium.GeoJson(
        iso_feature,
        style_function=lambda feature: {
            "fillColor": color,
            "color": color,
            "weight": 2,
            "fillOpacity": fill_opacity
        }
    ).add_to(fg)
    fg.add_to(m)

# ------------------------------------------------------------
# Функция добавления легенды с результатами доступности
# ------------------------------------------------------------
def add_legend_map(m, result):
    """Добавляет легенду с результатами проверки нормативов"""
    html = "<div style='position: fixed; bottom: 50px; left: 50px; width: 220px; height: auto; background-color: white; border:2px solid grey; z-index:9999; padding: 10px;'>"
    html += "<b>Результаты доступности:</b><br>"
    for obj_type, info in result.items():
        status = "ОК" if info["ok"] else "НЕ ОК"
        color = ISO_COLORS.get(obj_type, "gray")
        html += f"<i style='background:{color}; width:12px; height:12px; display:inline-block; margin-right:5px;'></i> {obj_type}: {status}<br>"
    html += "</div>"
    m.get_root().html.add_child(folium.Element(html))

# ------------------------------------------------------------
# Основная функция визуализации
# ------------------------------------------------------------
def visualize_accessibility(house_coord):
    # 1. Анализ доступности
    result = analyze_accessibility(house_coord)

    # 2. Стартовая карта
    m = folium.Map(location=house_coord[::-1], zoom_start=13)

    # 3. Дом
    fg_house = folium.FeatureGroup(name="Дом", show=True)
    folium.Marker(
        location=house_coord[::-1],
        popup="Дом",
        icon=folium.Icon(color="black", icon="home")
    ).add_to(fg_house)
    fg_house.add_to(m)

    # 4. Социальная инфраструктура
    fg_social = folium.FeatureGroup(name="Социальная инфраструктура", show=True)
    for _, row in SOCIAL_GDF.iterrows():
        amenity = row["amenity"]
        color = COLORS.get(amenity, "gray")
        folium.CircleMarker(
            location=(row.geometry.y, row.geometry.x),
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.8,
            popup=amenity
        ).add_to(fg_social)
    fg_social.add_to(m)

    # 5. Узлы дорог
    fg_nodes = folium.FeatureGroup(name="Узлы дорог", show=True)
    for _, row in NODES_GDF.iterrows():
        folium.CircleMarker(
            location=(row.geometry.y, row.geometry.x),
            radius=3,
            color="black",
            fill=True,
            fill_opacity=0.5,
            popup="Road Node"
        ).add_to(fg_nodes)
    fg_nodes.add_to(m)

    # 6. Изохроны по каждому типу
    for obj_type, info in result.items():
        color = ISO_COLORS.get(obj_type, "blue")
        if obj_type in ["kindergarten"]:
            add_isochrone_map(m, info["iso"], layer_name=f"{obj_type} изохрона", color=color)
        elif obj_type in ["school", "college"]:
            add_isochrone_map(m, info["iso_walk"], layer_name=f"{obj_type} изохрона пешком", color=color)
            add_isochrone_map(m, info["iso_drive"], layer_name=f"{obj_type} изохрона авто", color=color)
        elif obj_type in ["hospital"]:
            add_isochrone_map(m, info["iso_drive"], layer_name=f"{obj_type} изохрона авто", color=color)

    # 7. Легенда с результатами
    add_legend_map(m, result)

    # 8. Добавляем контроль слоёв
    folium.LayerControl(collapsed=False).add_to(m)

    # 9. Сохраняем карту
    output_file = os.path.join(BASE_DIR, "accessibility_map_ANALYS.html")
    m.save(output_file)
    print(f"Карта сохранена: {output_file}")

# ------------------------------------------------------------
# Пример запуска
# ------------------------------------------------------------
if __name__ == "__main__":
    house_coord = (29.434709583982123, 60.352912560887347)
    visualize_accessibility(house_coord)
