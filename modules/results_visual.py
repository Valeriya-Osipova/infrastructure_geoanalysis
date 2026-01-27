import folium
from shapely.geometry import shape
from main import run_analysis_and_suggestions

# Цвета для типов объектов
COLORS = {
    "kindergarten": "green",
    "school": "blue",
    "college": "purple",
    "hospital": "orange"
}

def visualize_result(house_coord, result, map_filename="accessibility_map.html"):
    fmap = folium.Map(location=(house_coord[1], house_coord[0]), zoom_start=14)

    # ------------------------------
    # 1. Дом
    # ------------------------------
    folium.Marker(
        location=(house_coord[1], house_coord[0]),
        popup="House",
        icon=folium.Icon(color="red", icon="home")
    ).add_to(fmap)

    # ------------------------------
    # 2. Изохроны
    # ------------------------------
    for obj_type, info in result["accessibility"].items():
        iso = info.get("iso") or info.get("iso_walk") or info.get("iso_drive")
        if iso:
            polygon = shape(iso["geometry"])
            folium.GeoJson(
                polygon,
                style_function=lambda feature, color=COLORS[obj_type]: {
                    "fillColor": color,
                    "color": color,
                    "weight": 2,
                    "fillOpacity": 0.2
                },
                tooltip=f"{obj_type} isochrone"
            ).add_to(fmap)

    # ------------------------------
    # 3. Предложенные участки
    # ------------------------------
    for obj_type, rec in result.get("recommendations", {}).items():
        sites = rec.get("recommended_sites", [])
        for pt in sites:
            folium.CircleMarker(
                location=(pt[1], pt[0]),
                radius=6,
                color=COLORS.get(obj_type, "gray"),
                fill=True,
                fill_opacity=0.7,
                popup=f"Proposed {obj_type}"
            ).add_to(fmap)

    # ------------------------------
    # 4. Сохранение карты
    # ------------------------------
    fmap.save(map_filename)
    print(f"Map saved to {map_filename}")


# ------------------------------
# Пример использования
# ------------------------------
if __name__ == "__main__":
    house_coord = (34.569816745664845, 61.631042923709295)
    result = run_analysis_and_suggestions(house_coord)
    visualize_result(house_coord, result)
