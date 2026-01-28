import os
from typing import Tuple, Dict, List, Any
import geopandas as gpd
from shapely.geometry import shape, Point
from scipy.spatial import KDTree
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESIDENTIAL_GDF = gpd.read_file(
    os.path.join(BASE_DIR, "../data/residential_buildings_points.geojson")
).set_crs(epsg=4326, allow_override=True)
LOW_DENSITY_GDF = gpd.read_file(
    os.path.join(BASE_DIR, "../data/final_areas.geojson")
).set_crs(epsg=4326, allow_override=True)

def find_residential_clusters(gdf: gpd.GeoDataFrame, radius_meters: float = 200, min_cluster_size: int = 3) -> List[Tuple[float, float]]:
    """Находит скопления домов и возвращает центроиды таких кластеров"""
    if len(gdf) == 0:
        return []
    
    centroid = gdf.unary_union.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    utm_epsg = 32600 + utm_zone
    gdf_utm = gdf.to_crs(epsg=utm_epsg)
    
    coords = np.array([[geom.x, geom.y] for geom in gdf_utm.geometry])
    tree = KDTree(coords)
    
    visited = set()
    cluster_centroids = []
    
    for idx, point in enumerate(coords):
        if idx in visited:
            continue
        indices = tree.query_ball_point(point, r=radius_meters)
        if len(indices) >= min_cluster_size:
            cluster_points = coords[indices]
            centroid_cluster = cluster_points.mean(axis=0)
            cluster_centroids.append(centroid_cluster)
            visited.update(indices)
    
    if not cluster_centroids:
        return []
    
    cluster_points_geom = gpd.GeoSeries(
        [Point(x, y) for x, y in cluster_centroids], 
        crs=utm_epsg
    )
    cluster_points_geom = cluster_points_geom.to_crs(epsg=4326)
    
    return [(pt.x, pt.y) for pt in cluster_points_geom]

def suggest_kindergarten(iso_feature: dict) -> Dict[str, Any]:
    """Предложения по размещению детского сада"""
    print("Suggesting kindergarten locations...")
    polygon = shape(iso_feature["geometry"])
    
    # 1. Ищем кластеры жилых зданий в изохронной зоне
    recommended_sites = []
    criteria_used = []
    
    # Получаем жилые здания в изохронной зоне
    residential_in_zone = RESIDENTIAL_GDF[
        RESIDENTIAL_GDF.geometry.apply(lambda x: polygon.contains(Point(x.x, x.y)) if hasattr(x, 'x') else polygon.contains(x))
    ]
    
    if not residential_in_zone.empty:
        # Находим кластеры среди этих зданий
        cluster_centers = find_residential_clusters(residential_in_zone)
        recommended_sites.extend(cluster_centers)
        if cluster_centers:
            criteria_used.append("clustered residential buildings within 500m walk isochrone")
    
    if not recommended_sites:
        # 2. Fallback: возвращаем всю изохронную зону
        criteria_used.append("fallback: full isochrone zone")
    
    return {
        "recommended_sites": recommended_sites,
        "fallback_zone": iso_feature if not recommended_sites else None,
        "criteria_used": criteria_used
    }

def suggest_school(iso_walk: dict, iso_drive: dict) -> Dict[str, Any]:
    """Предложения по размещению школы"""
    print("Suggesting school locations...")
    walk_polygon = shape(iso_walk["geometry"])
    drive_polygon = shape(iso_drive["geometry"])
    
    recommended_sites = []
    criteria_used = []
    
    # 1. Центры малонаселенных зон в пешей доступности
    for idx, row in LOW_DENSITY_GDF.iterrows():
        center = row.geometry.centroid
        if walk_polygon.contains(center):
            recommended_sites.append((center.x, center.y))
            criteria_used.append(f"zone_{idx}_center within walk isochrone")
            break  # Берем первую подходящую
    
    # 2. Кластеры жилых зданий в транспортной доступности
    if not recommended_sites:
        residential_in_drive = RESIDENTIAL_GDF[
            RESIDENTIAL_GDF.geometry.apply(lambda x: drive_polygon.contains(Point(x.x, x.y)) if hasattr(x, 'x') else drive_polygon.contains(x))
        ]
        
        if not residential_in_drive.empty:
            cluster_centers = find_residential_clusters(residential_in_drive)
            if cluster_centers:
                recommended_sites.extend(cluster_centers[:3])  # Берем первые 3 кластера
                criteria_used.append("clustered residential buildings within drive isochrone")
    
    if not recommended_sites:
        # 3. Fallback: возвращаем транспортную изохронную зону
        criteria_used.append("fallback: full drive isochrone zone")
    
    return {
        "recommended_sites": recommended_sites,
        "fallback_zone": iso_drive if not recommended_sites else None,
        "criteria_used": criteria_used
    }

def suggest_hospital(iso_feature: dict) -> Dict[str, Any]:
    """Предложения по размещению ФАПа (пешая 2км доступность)"""
    print("Suggesting FAP locations...")
    polygon = shape(iso_feature["geometry"])  # Пешая 2км изохрона
    
    recommended_sites = []
    criteria_used = []
    
    # 1. Центр малонаселенной зоны
    for idx, row in LOW_DENSITY_GDF.iterrows():
        center = row.geometry.centroid
        if polygon.contains(center):
            recommended_sites.append((center.x, center.y))
            criteria_used.append(f"zone_{idx}_center within 2km walk isochrone")
            break  # Берем первую подходящую
    
    # 2. Кластеры жилых зданий
    if not recommended_sites:
        residential_in_zone = RESIDENTIAL_GDF[
            RESIDENTIAL_GDF.geometry.apply(lambda x: polygon.contains(Point(x.x, x.y)) if hasattr(x, 'x') else polygon.contains(x))
        ]
        
        if not residential_in_zone.empty:
            cluster_centers = find_residential_clusters(residential_in_zone)
            if cluster_centers:
                recommended_sites.extend(cluster_centers[:2])  # Берем первые 2 кластера
                criteria_used.append("clustered residential buildings within 2km walk isochrone")
    
    if not recommended_sites:
        # 3. Fallback: возвращаем всю изохронную зону
        criteria_used.append("fallback: full 2km walk isochrone zone")
    
    return {
        "recommended_sites": recommended_sites,
        "fallback_zone": iso_feature if not recommended_sites else None,
        "criteria_used": criteria_used
    }

def generate_placement_suggestions(accessibility_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Генерирует рекомендации по размещению для объектов с нарушенными нормативами
    
    Parameters:
        accessibility_result: результат функции analyze_accessibility
        
    Returns:
        Обновленный словарь с заполненными полями "suggestions" для объектов с ok=False
    """
    result = accessibility_result.copy()
    
    # Для детского сада
    if not result["kindergarten"]["ok"]:
        suggestions = suggest_kindergarten(result["kindergarten"]["iso"])
        result["kindergarten"]["suggestions"] = suggestions
    
    # Для школы
    if not result["school"]["ok"]:
        suggestions = suggest_school(
            result["school"]["iso_walk"],
            result["school"]["iso_drive"]
        )
        result["school"]["suggestions"] = suggestions
    
    # Для ФАПа
    if not result["hospital"]["ok"]:
        suggestions = suggest_hospital(result["hospital"]["iso"])
        result["hospital"]["suggestions"] = suggestions
    
    return result

def placement_suggestions(object_type: str, iso_walk: dict = None, iso_drive: dict = None) -> Dict[str, Any]:
    """
    Устаревшая функция для обратной совместимости.
    Рекомендуется использовать generate_placement_suggestions()
    """
    if object_type == "kindergarten":
        return suggest_kindergarten(iso_walk)
    elif object_type == "school":
        return suggest_school(iso_walk, iso_drive)
    elif object_type == "hospital":
        return suggest_hospital(iso_walk)  # Для ФАПа используем пешую изохрону
    else:
        raise ValueError(f"Unknown object type: {object_type}")