import sys
import os
from typing import Tuple, Dict, Any

# ------------------------------------------------------------
# Добавляем модули в путь
# ------------------------------------------------------------
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from accessibility_module import analyze_accessibility
from placement_module import placement_suggestions

# ------------------------------------------------------------
# Главная функция анализа + генерации предложений
# ------------------------------------------------------------
def run_analysis_and_suggestions(house_coord: Tuple[float, float]) -> Dict[str, Any]:
    """
    Анализ доступности и генерация рекомендаций по размещению недостающих объектов.

    Parameters
    ----------
    house_coord : tuple
        Координаты жилого дома (lon, lat)

    Returns
    -------
    dict
        {
            "accessibility": {...},         # Результаты анализа доступности
            "recommendations": {...}        # Предложения по размещению для нарушений
        }
    """
    result = analyze_accessibility(house_coord)
    recommendations = {}

    # Для каждого типа проверяем, есть ли нарушение
    for obj_type, info in result.items():
        if obj_type == "kindergarten" or obj_type == "hospital":
            iso = info.get("iso") or info.get("iso_drive")
        elif obj_type == "school" or obj_type == "college":
            # Проверяем сначала пешую изохрону
            iso = info.get("iso_walk") or info.get("iso_drive")
        else:
            continue

        if not info["ok"]:
            # Передаем изохрону в модуль размещения
            rec = placement_suggestions(obj_type=obj_type, broken_iso=iso)
            recommendations[obj_type] = rec

    return {
        "accessibility": result,
        "recommendations": recommendations
    }

# ------------------------------------------------------------
# Пример запуска
# ------------------------------------------------------------
if __name__ == "__main__":
    # Пример координат дома
    house_coord = (34.569816745664845, 61.631042923709295)
    
    analysis_result = run_analysis_and_suggestions(house_coord)
    
    # Печатаем доступность
    print("=== Accessibility Results ===")
    for obj_type, info in analysis_result["accessibility"].items():
        print(f"{obj_type}: {info['ok']}")

    # Печатаем рекомендации
    print("\n=== Placement Recommendations ===")
    for obj_type, rec in analysis_result["recommendations"].items():
        print(f"{obj_type}:")
        for key, val in rec.items():
            print(f"  {key}: {val}")
