"""
Тестирование и визуализация изохрон
----------------------------------
• Загружает модуль построения изохрон
• Строит walk / drive изохроны
• Визуализирует результат на интерактивной HTML-карте
"""

from pathlib import Path
import json

import folium
from shapely.geometry import shape, Point

from isochrones_module import build_isochrone


# ============================================================
# ПАРАМЕТРЫ ТЕСТА
# ============================================================

CENTER_POINT = (29.439677388032283, 60.35427692140108)   # (lon, lat)
OUTPUT_HTML = "isochrones_test_map.html"

TEST_CASES = [
    {
        "mode": "walk",
        "limit": 500,
        "limit_type": "meters",
        "color": "#2ecc71"
    },
    {
        "mode": "drive",
        "limit": 20,
        "limit_type": "minutes",
        "color": "#3498db"
    }
]


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def _add_isochrone_to_map(
    fmap: folium.Map,
    feature: dict,
    color: str
) -> None:
    """Добавляет GeoJSON-изохрону на карту"""

    folium.GeoJson(
        data=feature,
        style_function=lambda _: {
            "fillColor": color,
            "color": color,
            "weight": 2,
            "fillOpacity": 0.35
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "mode",
                "limit",
                "limit_type",
                "reachable_nodes"
            ],
            aliases=[
                "Режим",
                "Ограничение",
                "Тип",
                "Узлов"
            ]
        )
    ).add_to(fmap)


# ============================================================
# ОСНОВНОЙ СЦЕНАРИЙ
# ============================================================

def main() -> None:

    # --- базовая карта ---
    fmap = folium.Map(
        location=(CENTER_POINT[1], CENTER_POINT[0]),
        zoom_start=13,
        tiles="cartodbpositron"
    )

    # --- точка старта ---
    folium.Marker(
        location=(CENTER_POINT[1], CENTER_POINT[0]),
        tooltip="Точка старта",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(fmap)

    # --- построение изохрон ---
    for case in TEST_CASES:
        print(
            f"Строится изохрона: "
            f"{case['mode']} | {case['limit']} {case['limit_type']}"
        )

        feature = build_isochrone(
            coord=CENTER_POINT,
            mode=case["mode"],
            limit=case["limit"],
            limit_type=case["limit_type"]
        )

        _add_isochrone_to_map(
            fmap=fmap,
            feature=feature,
            color=case["color"]
        )

    # --- слой управления ---
    folium.LayerControl(collapsed=False).add_to(fmap)

    # --- сохранение ---
    fmap.save(OUTPUT_HTML)
    print(f"HTML-карта сохранена: {OUTPUT_HTML}")


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    main()
