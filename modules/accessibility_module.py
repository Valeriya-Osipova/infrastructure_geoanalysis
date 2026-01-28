from typing import Tuple, Dict, Any
import os
import geopandas as gpd
from shapely.geometry import Point, shape

from isochrones_module import build_isochrone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOCIAL_GDF = gpd.read_file(
    os.path.join(BASE_DIR, "../data/social_infrastructure_points.geojson")
).set_crs(epsg=4326, allow_override=True)

def _check_in_isochron(iso_feature: dict, point: Point) -> bool:
    """Проверяет, попадает ли точка в изохронную зону"""
    polygon = shape(iso_feature["geometry"])
    return polygon.contains(point)

def _check_kindergarten(coord: Tuple[float, float]) -> Tuple[bool, dict]:
    """Проверка доступности детского сада (только пешая 500м)"""
    print("Checking kindergarten accessibility...")
    iso = build_isochrone(coord, mode="walk", limit=500, limit_type="meters")
    kids = SOCIAL_GDF[SOCIAL_GDF["amenity"] == "kindergarten"]
    kids_points = [Point(x, y) for x, y in zip(kids.geometry.x, kids.geometry.y)]
    result = any(_check_in_isochron(iso, pt) for pt in kids_points)
    return result, iso

def _check_school(coord: Tuple[float, float]) -> Tuple[bool, dict, dict]:
    """Проверка доступности школы (пешая 500м или транспортная 15мин)"""
    print("Checking school accessibility...")
    iso_walk = build_isochrone(coord, mode="walk", limit=500, limit_type="meters")
    iso_drive = build_isochrone(coord, mode="drive", limit=15, limit_type="minutes")
    schools = SOCIAL_GDF[SOCIAL_GDF["amenity"] == "school"]
    schools_points = [Point(x, y) for x, y in zip(schools.geometry.x, schools.geometry.y)]
    result = any(_check_in_isochron(iso_walk, pt) for pt in schools_points) or \
             any(_check_in_isochron(iso_drive, pt) for pt in schools_points)
    return result, iso_walk, iso_drive

def _check_hospital(coord: Tuple[float, float]) -> Tuple[bool, dict]:
    """Проверка доступности ФАПа (пешая 2км)"""
    print("Checking FAP accessibility...")
    iso_walk = build_isochrone(coord, mode="walk", limit=2000, limit_type="meters")  # 2км
    hospitals = SOCIAL_GDF[SOCIAL_GDF["amenity"].isin(["clinic"])]  # Только ФАПы
    hospitals_points = [Point(x, y) for x, y in zip(hospitals.geometry.x, hospitals.geometry.y)]
    result = any(_check_in_isochron(iso_walk, pt) for pt in hospitals_points)
    return result, iso_walk

def analyze_accessibility(coord: Tuple[float, float]) -> Dict[str, Any]:
    """
    Проверка соблюдения нормативов доступности для заданного дома.
    
    Returns:
        Dict с ключами: kindergarten, school, hospital
        Каждый ключ содержит:
            - "ok": True/False (соблюдается ли норматив)
            - "iso": изохронная зона для проверки (или несколько для школы)
            - "suggestions": рекомендации по размещению (если ok=False)
    """
    # Проверяем доступность для каждого типа объектов
    kindergarten_ok, kindergarten_iso = _check_kindergarten(coord)
    school_ok, school_iso_walk, school_iso_drive = _check_school(coord)
    hospital_ok, hospital_iso = _check_hospital(coord)
    
    # Формируем результат
    result = {
        "kindergarten": {
            "ok": kindergarten_ok,
            "iso": kindergarten_iso,
            "suggestions": []  # Заполнится позже если ok=False
        },
        "school": {
            "ok": school_ok,
            "iso_walk": school_iso_walk,
            "iso_drive": school_iso_drive,
            "suggestions": []
        },
        "hospital": {
            "ok": hospital_ok,
            "iso": hospital_iso,  # Только пешая изохрона для ФАПа
            "suggestions": []
        }
    }
    
    return result