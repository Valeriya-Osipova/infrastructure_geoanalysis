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
    polygon = shape(iso_feature["geometry"])
    return polygon.contains(point)

def _check_kindergarten(coord: Tuple[float, float]) -> Tuple[bool, dict]:
    print("Checking kindergarten accessibility...")
    iso = build_isochrone(coord, mode="walk", limit=500, limit_type="meters")
    kids = SOCIAL_GDF[SOCIAL_GDF["amenity"] == "kindergarten"]
    kids_points = [Point(x, y) for x, y in zip(kids.geometry.x, kids.geometry.y)]
    result = any(_check_in_isochron(iso, pt) for pt in kids_points)
    return result, iso

def _check_school(coord: Tuple[float, float]) -> Tuple[bool, dict, dict]:
    print("Checking school accessibility...")
    iso_walk = build_isochrone(coord, mode="walk", limit=500, limit_type="meters")
    iso_drive = build_isochrone(coord, mode="drive", limit=15, limit_type="minutes")
    schools = SOCIAL_GDF[SOCIAL_GDF["amenity"] == "school"]
    schools_points = [Point(x, y) for x, y in zip(schools.geometry.x, schools.geometry.y)]
    result = any(_check_in_isochron(iso_walk, pt) for pt in schools_points) or \
             any(_check_in_isochron(iso_drive, pt) for pt in schools_points)
    return result, iso_walk, iso_drive

def _check_college(coord: Tuple[float, float]) -> Tuple[bool, dict, dict]:
    print("Checking college accessibility...")
    iso_walk = build_isochrone(coord, mode="walk", limit=500, limit_type="meters")
    iso_drive = build_isochrone(coord, mode="drive", limit=30, limit_type="minutes")
    colleges = SOCIAL_GDF[SOCIAL_GDF["amenity"] == "college"]
    colleges_points = [Point(x, y) for x, y in zip(colleges.geometry.x, colleges.geometry.y)]
    result = any(_check_in_isochron(iso_walk, pt) for pt in colleges_points) or \
             any(_check_in_isochron(iso_drive, pt) for pt in colleges_points)
    return result, iso_walk, iso_drive

def _check_hospital(coord: Tuple[float, float]) -> Tuple[bool, dict]:
    print("Checking hospital accessibility...")
    iso_drive = build_isochrone(coord, mode="drive", limit=30, limit_type="minutes")
    hospitals = SOCIAL_GDF[SOCIAL_GDF["amenity"].isin(["hospital", "clinic"])]
    hospitals_points = [Point(x, y) for x, y in zip(hospitals.geometry.x, hospitals.geometry.y)]
    result = any(_check_in_isochron(iso_drive, pt) for pt in hospitals_points)
    return result, iso_drive

def analyze_accessibility(coord: Tuple[float, float]) -> Dict[str, Any]:
    """
    Проверка соблюдения нормативов доступности для заданного дома.
    Возвращает словарь с True/False и изохронными зонами для каждого типа.
    """
    kindergarten_ok, kindergarten_iso = _check_kindergarten(coord)
    school_ok, school_iso_walk, school_iso_drive = _check_school(coord)
    college_ok, college_iso_walk, college_iso_drive = _check_college(coord)
    hospital_ok, hospital_iso_drive = _check_hospital(coord)
    
    return {
        "kindergarten": {"ok": kindergarten_ok, "iso": kindergarten_iso},
        "school": {"ok": school_ok, "iso_walk": school_iso_walk, "iso_drive": school_iso_drive},
        "college": {"ok": college_ok, "iso_walk": college_iso_walk, "iso_drive": college_iso_drive},
        "hospital": {"ok": hospital_ok, "iso_drive": hospital_iso_drive}
    }