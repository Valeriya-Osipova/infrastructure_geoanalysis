import os
from typing import Tuple, Any
import geopandas as gpd
from shapely.geometry import shape, Point
import folium

from accessibility_module import analyze_accessibility
from placement_module import placement_suggestions

# ------------------------------------------------------------
# Пример координат жилого дома
# ------------------------------------------------------------
HOUSE_COORD = (31.321001, 56.2755187)

# ------------------------------------------------------------
# Цвета по типу инфраструктуры
# ------------------------------------------------------------
COLORS = {
    "kindergarten": "green",
    "school": "orange",
    "college": "purple",
    "hospital": "red"
}

# ------------------------------------------------------------
# Функция визуализации
# ------------------------------------------------------------
def visualize_results(accessibility: dict, recommendations: dict, house_coord: Tuple[float, float]):
    # Центрируем карту на доме
    m = folium.Map(location=[house_coord[1], house_coord[0]], zoom_start=13)

    # FeatureGroup для дома
    fg_house = folium.FeatureGroup(name="Дом")
    folium.Marker(
        location=[house_coord[1], house_coord[0]],
        popup="Жилой дом",
        icon=folium.Icon(color="blue", icon="home")
    ).add_to(fg_house)
    fg_house.add_to(m)

    # FeatureGroup для изохрон
    for obj_type, info in accessibility.items():
        fg_iso = folium.FeatureGroup(name=f"{obj_type} изохроны")
        color = COLORS.get(obj_type, "gray")
        if obj_type == "kindergarten":
            iso = info.get("iso")
            if iso:
                folium.GeoJson(
                    shape(iso["geometry"]),
                    style_function=lambda x, c=color: {"fillColor": c, "color": c, "weight": 2, "fillOpacity": 0.2},
                    tooltip=f"{obj_type} Isochron"
                ).add_to(fg_iso)
        elif obj_type in ["school", "college"]:
            iso_walk = info.get("iso_walk")
            iso_drive = info.get("iso_drive")
            if iso_walk:
                folium.GeoJson(
                    shape(iso_walk["geometry"]),
                    style_function=lambda x, c=color: {"fillColor": c, "color": c, "weight": 2, "fillOpacity": 0.2},
                    tooltip=f"{obj_type} Isochron пешком"
                ).add_to(fg_iso)
            if iso_drive:
                folium.GeoJson(
                    shape(iso_drive["geometry"]),
                    style_function=lambda x, c=color: {"fillColor": c, "color": c, "weight": 2, "fillOpacity": 0.2},
                    tooltip=f"{obj_type} Isochron авто"
                ).add_to(fg_iso)
        elif obj_type == "hospital":
            iso_drive = info.get("iso_drive")
            if iso_drive:
                folium.GeoJson(
                    shape(iso_drive["geometry"]),
                    style_function=lambda x, c=color: {"fillColor": c, "color": c, "weight": 2, "fillOpacity": 0.2},
                    tooltip=f"{obj_type} Isochron авто"
                ).add_to(fg_iso)
        fg_iso.add_to(m)

    # FeatureGroup для рекомендованных участков
    for obj_type, rec in recommendations.items():
        fg_rec = folium.FeatureGroup(name=f"Рекомендации: {obj_type}")
        for pt in rec.get("recommended_sites", []):
            folium.Marker(
                location=[pt[1], pt[0]],
                popup=f"Recommended {obj_type}",
                icon=folium.Icon(color=COLORS[obj_type], icon="plus")
            ).add_to(fg_rec)
        fg_rec.add_to(m)

    # --------------------------------------------------------
    # Легенда с отчетом доступности
    # --------------------------------------------------------
    html = "<div style='position: fixed; bottom: 50px; left: 50px; width: 250px; background-color: white; border:2px solid grey; z-index:9999; padding: 10px;'>"
    html += "<b>Результаты доступности:</b><br>"
    for obj_type, info in accessibility.items():
        status = "OK" if info["ok"] else "NOT OK"
        color = COLORS.get(obj_type, "gray")
        html += f"<i style='background:{color}; width:12px; height:12px; display:inline-block; margin-right:5px;'></i> {obj_type}: {status}<br>"
    html += "</div>"
    m.get_root().html.add_child(folium.Element(html))

    # --------------------------------------------------------
    # Контроль слоев
    # --------------------------------------------------------
    folium.LayerControl(collapsed=False).add_to(m)

    # --------------------------------------------------------
    # Сохраняем карту
    # --------------------------------------------------------
    output_map = os.path.join(os.path.dirname(__file__), "accessibility_map_RESULTS.html")
    m.save(output_map)
    print(f"Карта сохранена: {output_map}")

# ------------------------------------------------------------
# Текстовый отчет
# ------------------------------------------------------------
def print_report(accessibility: dict, recommendations: dict):
    print("=== Accessibility Report ===")
    for obj_type, info in accessibility.items():
        status = "OK" if info["ok"] else "NOT OK"
        print(f"{obj_type}: {status}")
    
    print("\n=== Placement Recommendations ===")
    for obj_type, rec in recommendations.items():
        print(f"{obj_type}:")
        print(f"  Criteria used: {rec['criteria_used']}")
        print(f"  Recommended sites: {rec['recommended_sites']}")
        print(f"  Fallback zone geometry type: {rec['fallback_zone']['geometry']['type']}")

# ------------------------------------------------------------
# Запуск анализа + предложений
# ------------------------------------------------------------
def test_accessibility_and_placement(house_coord: Tuple[float, float]):
    # 1. Проверка доступности
    accessibility = analyze_accessibility(house_coord)
    
    # 2. Генерация рекомендаций
    recommendations = {}
    for obj_type, info in accessibility.items():
        if info["ok"]:
            continue
        
        if obj_type == "kindergarten":
            rec = placement_suggestions(object_type="kindergarten", iso_walk=info.get("iso"))
        elif obj_type in ["school", "college"]:
            rec = placement_suggestions(object_type=obj_type, 
                                        iso_walk=info.get("iso_walk"), 
                                        iso_drive=info.get("iso_drive"))
        elif obj_type == "hospital":
            rec = placement_suggestions(object_type="hospital", iso_drive=info.get("iso_drive"))
        else:
            continue
        recommendations[obj_type] = rec
    
    # 3. Вывод отчета
    print_report(accessibility, recommendations)
    
    # 4. Визуализация
    visualize_results(accessibility, recommendations, house_coord)

# ------------------------------------------------------------
# Запуск
# ------------------------------------------------------------
if __name__ == "__main__":
    test_accessibility_and_placement(HOUSE_COORD)
