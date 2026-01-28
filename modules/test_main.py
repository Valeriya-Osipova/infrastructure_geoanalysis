# accessibility_visualization.py

import folium
from folium.plugins import MeasureControl, Fullscreen, MousePosition
import geopandas as gpd
from shapely.geometry import Point
import json
import os
from typing import Dict, Any, Tuple, List

# Импорт ваших модулей
from accessibility_module import analyze_accessibility
from placement_module import generate_placement_suggestions

class AccessibilityVisualizer:
    def __init__(self, output_dir="output_maps"):
        """Инициализация визуализатора"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Цвета для разных типов объектов
        self.colors = {
            'kindergarten': '#FFD700',  # золотой
            'school': '#1E90FF',        # синий
            'hospital': '#DC143C',      # красный
            'residential': '#228B22',   # зеленый
            'infrastructure': '#8A2BE2', # фиолетовый
            'suggestions': '#FF4500'    # оранжевый
        }
        
    def create_base_map(self, center_coords: Tuple[float, float], zoom_start: int = 13) -> folium.Map:
        """
        Создает базовую карту с контролами
        
        Args:
            center_coords: координаты центра карты (широта, долгота)
            zoom_start: начальный уровень зума
            
        Returns:
            Объект карты folium.Map
        """
        print(f"Создание карты с центром в {center_coords}")
        
        m = folium.Map(
            location=center_coords,
            zoom_start=zoom_start,
            tiles='OpenStreetMap',
            control_scale=True
        )
        
        # Добавляем полезные плагины
        MeasureControl().add_to(m)
        Fullscreen().add_to(m)
        MousePosition().add_to(m)
        
        # Добавляем альтернативные тайлы
        folium.TileLayer(
            'CartoDB positron',
            name='Светлая карта',
            attr='CartoDB'
        ).add_to(m)
        
        folium.TileLayer(
            'CartoDB dark_matter',
            name='Темная карта',
            attr='CartoDB'
        ).add_to(m)
        
        return m
    
    def add_residential_point(self, m: folium.Map, coord: Tuple[float, float], house_id: str = "test_house") -> folium.Map:
        """
        Добавляет точку жилого дома на карту
        
        Args:
            m: объект карты folium
            coord: координаты дома (долгота, широта)
            house_id: идентификатор дома
            
        Returns:
            Обновленная карта
        """
        print(f"Добавление жилого дома {house_id}")
        
        # Создаем FeatureGroup для жилых домов
        residential_group = folium.FeatureGroup(name="Жилые дома", show=True)
        
        folium.Marker(
            location=[coord[1], coord[0]],  # [lat, lon]
            popup=f"""
            <div style="min-width: 200px;">
                <h4>Жилой дом {house_id}</h4>
                <p><b>Координаты:</b><br>
                Широта: {coord[1]:.5f}<br>
                Долгота: {coord[0]:.5f}</p>
                <p><b>Тип:</b> Точка анализа доступности</p>
            </div>
            """,
            tooltip="Жилой дом (точка анализа)",
            icon=folium.Icon(color='green', icon='home', prefix='fa')
        ).add_to(residential_group)
        
        residential_group.add_to(m)
        return m
    
    def load_infrastructure_data(self, data_path: str = "../data/social_infrastructure_points.geojson") -> gpd.GeoDataFrame:
        """
        Загружает данные об инфраструктуре из GeoJSON
        
        Args:
            data_path: путь к файлу с данными
            
        Returns:
            GeoDataFrame с объектами инфраструктуры
        """
        print(f"Загрузка инфраструктуры из {data_path}")
        
        try:
            gdf = gpd.read_file(data_path)
            if gdf.crs is None:
                gdf = gdf.set_crs(epsg=4326, allow_override=True)
            else:
                gdf = gdf.to_crs(epsg=4326)
            
            print(f"Загружено {len(gdf)} объектов инфраструктуры")
            return gdf
            
        except Exception as e:
            print(f"Ошибка при загрузке инфраструктуры: {e}")
            return gpd.GeoDataFrame()
    
    def add_infrastructure_points(self, m: folium.Map, gdf: gpd.GeoDataFrame) -> bool:
        """
        Добавляет точки социальной инфраструктуры на карту
        
        Args:
            m: объект карты folium
            gdf: GeoDataFrame с данными инфраструктуры
            
        Returns:
            True если успешно, False если ошибка
        """
        if gdf.empty:
            print("Нет данных об инфраструктуре для отображения")
            return False
        
        print(f"Добавление {len(gdf)} объектов инфраструктуры на карту")
        
        # Создаем FeatureGroup для управления видимостью
        infra_group = folium.FeatureGroup(name="Существующая инфраструктура", show=True)
        
        # Счетчики по типам
        type_counts = {'kindergarten': 0, 'school': 0, 'clinic': 0, 'other': 0}
        
        for idx, row in gdf.iterrows():
            if row.geometry and not row.geometry.is_empty:
                # Определяем тип объекта по amenity
                amenity = str(row.get('amenity', 'unknown')).lower()
                
                # Настраиваем иконку в зависимости от типа
                if 'kindergarten' in amenity or 'детсад' in str(row.get('name', '')).lower():
                    icon_color = self.colors['kindergarten']
                    icon_name = 'child'
                    type_name = 'Детский сад'
                    type_counts['kindergarten'] += 1
                elif 'school' in amenity or 'школа' in str(row.get('name', '')).lower():
                    icon_color = self.colors['school']
                    icon_name = 'graduation-cap'
                    type_name = 'Школа'
                    type_counts['school'] += 1
                elif 'clinic' in amenity or 'фак' in str(row.get('name', '')).lower():
                    icon_color = self.colors['hospital']
                    icon_name = 'medkit'
                    type_name = 'ФАП'
                    type_counts['clinic'] += 1
                else:
                    icon_color = 'gray'
                    icon_name = 'info-circle'
                    type_name = 'Другой'
                    type_counts['other'] += 1
                
                # Получаем координаты
                try:
                    if hasattr(row.geometry, 'x'):
                        lon, lat = row.geometry.x, row.geometry.y
                    else:
                        centroid = row.geometry.centroid
                        lon, lat = centroid.x, centroid.y
                    
                    # Создаем всплывающее окно с информацией
                    name = row.get('name', 'Не указано')
                    popup_html = f"""
                    <div style="min-width: 250px;">
                        <h4>{type_name}</h4>
                        <p><b>Название:</b> {name}</p>
                        <p><b>Тип:</b> {amenity}</p>
                        <p><b>Координаты:</b><br>
                        Широта: {lat:.5f}<br>
                        Долгота: {lon:.5f}</p>
                        <p><b>ID в базе:</b> {idx}</p>
                    </div>
                    """
                    
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"{type_name}: {name}",
                        icon=folium.Icon(color=icon_color.lower(), icon=icon_name, prefix='fa')
                    ).add_to(infra_group)
                    
                except Exception as e:
                    print(f"Ошибка при обработке объекта {idx}: {e}")
        
        infra_group.add_to(m)
        
        print(f"Статистика инфраструктуры: {type_counts}")
        return True
    
    def add_isochrones(self, m: folium.Map, accessibility_result: Dict[str, Any]) -> folium.FeatureGroup:
        """
        Добавляет изохронные зоны на карту
        
        Args:
            m: объект карты folium
            accessibility_result: результат анализа доступности
            
        Returns:
            FeatureGroup с изохронными зонами
        """
        print("Добавление изохронных зон на карту")
        
        isochrone_group = folium.FeatureGroup(name="Изохронные зоны доступности", show=True)
        
        # Стили для разных типов изохрон
        isochrone_styles = {
            'kindergarten': {
                'color': '#FFD700',  # золотой
                'fillColor': '#FFD700',
                'weight': 2,
                'fillOpacity': 0.15,
                'dashArray': None,
                'className': 'kindergarten-isochrone'
            },
            'school_walk': {
                'color': '#1E90FF',  # синий
                'fillColor': '#1E90FF',
                'weight': 2,
                'fillOpacity': 0.15,
                'dashArray': '5, 5',
                'className': 'school-walk-isochrone'
            },
            'school_drive': {
                'color': '#1E90FF',  # синий
                'fillColor': '#1E90FF',
                'weight': 2,
                'fillOpacity': 0.08,
                'dashArray': None,
                'className': 'school-drive-isochrone'
            },
            'hospital': {
                'color': '#DC143C',  # красный
                'fillColor': '#DC143C',
                'weight': 2,
                'fillOpacity': 0.15,
                'dashArray': '10, 5',
                'className': 'hospital-isochrone'
            }
        }
        
        # Добавляем изохроны для каждого типа объекта
        isochrones_added = 0
        
        # Детский сад (пешая 500м)
        kindergarten_data = accessibility_result.get('kindergarten', {})
        if 'iso' in kindergarten_data and kindergarten_data['iso']:
            iso_kindergarten = kindergarten_data['iso']
            if iso_kindergarten.get('geometry'):
                folium.GeoJson(
                    iso_kindergarten,
                    name='Детский сад (500м пешком)',
                    style_function=lambda x: isochrone_styles['kindergarten'],
                    tooltip="Зона пешей доступности 500м для детского сада",
                    popup=folium.Popup(
                        "<b>Детский сад</b><br>Зона пешей доступности 500м<br>"
                        "Норматив: СП 42.13330.2016",
                        max_width=200
                    )
                ).add_to(isochrone_group)
                isochrones_added += 1
        
        # Школа (пешая 500м и транспортная 15мин)
        school_data = accessibility_result.get('school', {})
        if 'iso_walk' in school_data and school_data['iso_walk']:
            iso_school_walk = school_data['iso_walk']
            if iso_school_walk.get('geometry'):
                folium.GeoJson(
                    iso_school_walk,
                    name='Школа (500м пешком)',
                    style_function=lambda x: isochrone_styles['school_walk'],
                    tooltip="Зона пешей доступности 500м для школы",
                    popup=folium.Popup(
                        "<b>Школа</b><br>Зона пешей доступности 500м<br>"
                        "Норматив: СП 42.13330.2016",
                        max_width=200
                    )
                ).add_to(isochrone_group)
                isochrones_added += 1
        
        if 'iso_drive' in school_data and school_data['iso_drive']:
            iso_school_drive = school_data['iso_drive']
            if iso_school_drive.get('geometry'):
                folium.GeoJson(
                    iso_school_drive,
                    name='Школа (15 мин транспортом)',
                    style_function=lambda x: isochrone_styles['school_drive'],
                    tooltip="Зона транспортной доступности 15 минут для школы",
                    popup=folium.Popup(
                        "<b>Школа</b><br>Зона транспортной доступности 15 мин<br>"
                        "Норматив: СП 42.13330.2016",
                        max_width=200
                    )
                ).add_to(isochrone_group)
                isochrones_added += 1
        
        # ФАП (пешая 2км)
        hospital_data = accessibility_result.get('hospital', {})
        if 'iso' in hospital_data and hospital_data['iso']:
            iso_hospital = hospital_data['iso']
            if iso_hospital.get('geometry'):
                folium.GeoJson(
                    iso_hospital,
                    name='ФАП (2км пешком)',
                    style_function=lambda x: isochrone_styles['hospital'],
                    tooltip="Зона пешей доступности 2км для ФАПа",
                    popup=folium.Popup(
                        "<b>ФАП</b><br>Зона пешей доступности 2000м<br>"
                        "Норматив: Приказ Минздрава №132н",
                        max_width=200
                    )
                ).add_to(isochrone_group)
                isochrones_added += 1
        
        isochrone_group.add_to(m)
        print(f"Добавлено {isochrones_added} изохронных зон")
        return isochrone_group
    
    def add_placement_suggestions(self, m: folium.Map, final_result: Dict[str, Any]) -> folium.FeatureGroup:
        """
        Добавляет предложения по размещению на карту
        
        Args:
            m: объект карты folium
            final_result: полный результат анализа с предложениями
            
        Returns:
            FeatureGroup с предложениями по размещению
        """
        print("Добавление предложений по размещению на карту")
        
        suggestions_group = folium.FeatureGroup(name="Предложения по размещению", show=True)
        
        # Цвета и иконки для разных типов предложений
        suggestion_config = {
            'kindergarten': {
                'color': '#FFD700',      # золотой
                'icon': 'child',
                'name': 'Детский сад',
                'icon_color': 'orange'
            },
            'school': {
                'color': '#1E90FF',      # синий
                'icon': 'graduation-cap',
                'name': 'Школа',
                'icon_color': 'blue'
            },
            'hospital': {
                'color': '#DC143C',      # красный
                'icon': 'medkit',
                'name': 'ФАП',
                'icon_color': 'red'
            }
        }
        
        suggestions_added = 0
        
        for obj_type, config in suggestion_config.items():
            data = final_result.get(obj_type, {})
            
            # Проверяем, нарушен ли норматив и есть ли предложения
            if not data.get('ok', True) and data.get('suggestions'):
                suggestions = data['suggestions']
                recommended_sites = suggestions.get('recommended_sites', [])
                
                # Добавляем каждое предложенное место
                for i, (lon, lat) in enumerate(recommended_sites, 1):
                    popup_html = f"""
                    <div style="min-width: 250px;">
                        <h4>Предложение по размещению</h4>
                        <p><b>Тип объекта:</b> {config['name']}</p>
                        <p><b>Ранг в рекомендациях:</b> {i}/{len(recommended_sites)}</p>
                        <p><b>Координаты:</b><br>
                        Широта: {lat:.5f}<br>
                        Долгота: {lon:.5f}</p>
                        <p><b>Статус:</b> Рекомендовано</p>
                        <p><b>Критерии выбора:</b><br>
                        {', '.join(suggestions.get('criteria_used', ['Не указаны']))}</p>
                        <hr>
                        <p style="font-size: 0.9em; color: #666;">
                        <i>Это предложение сгенерировано алгоритмом на основе 
                        анализа доступности и пространственных закономерностей</i></p>
                    </div>
                    """
                    
                    # Создаем маркер с номером
                    icon_html = f"""
                    <div style="
                        background-color: {config['color']};
                        border: 2px solid white;
                        border-radius: 50%;
                        width: 32px;
                        height: 32px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-weight: bold;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                    ">
                        {i}
                    </div>
                    """
                    
                    icon = folium.DivIcon(
                    html=icon_html,
                    icon_size=(32, 32),
                    icon_anchor=(16, 16)
                )
                    
                    # Добавляем маркер
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"Предложение: {config['name']} (ранг {i})",
                        icon=icon
                    ).add_to(suggestions_group)
                    
                    suggestions_added += 1
                
                # Добавляем fallback зону, если есть
                fallback_zone = suggestions.get('fallback_zone')
                if fallback_zone and fallback_zone.get('geometry'):
                    folium.GeoJson(
                        fallback_zone,
                        name=f'Зона поиска для {config["name"]}',
                        style_function=lambda x, color=config['color']: {
                            'fillColor': color,
                            'color': color,
                            'weight': 3,
                            'dashArray': '5, 5',
                            'fillOpacity': 0.1
                        },
                        tooltip=f"Зона поиска для {config['name']} (резервный вариант)"
                    ).add_to(suggestions_group)
        
        suggestions_group.add_to(m)
        print(f"Добавлено {suggestions_added} предложений по размещению")
        return suggestions_group
    
    def add_legend(self, m: folium.Map, final_result: Dict[str, Any]) -> None:
        """
        Добавляет легенду с результатами анализа на карту
        
        Args:
            m: объект карты folium
            final_result: полный результат анализа
        """
        print("Добавление легенды на карту")
        
        # HTML для легенды
        legend_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                #legend-container {
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    width: 350px;
                    max-height: 80vh;
                    background-color: white;
                    border: 2px solid #007bff;
                    border-radius: 8px;
                    padding: 15px;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    z-index: 1000;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                    overflow-y: auto;
                    transition: all 0.3s ease;
                }
                
                #legend-container.collapsed {
                    height: 40px;
                    overflow: hidden;
                }
                
                .legend-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid #ddd;
                }
                
                .legend-title {
                    font-size: 16px;
                    font-weight: bold;
                    color: #007bff;
                }
                
                .toggle-btn {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 10px;
                    cursor: pointer;
                    font-size: 11px;
                }
                
                .toggle-btn:hover {
                    background-color: #0056b3;
                }
                
                .result-item {
                    margin-bottom: 12px;
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #f8f9fa;
                    border-left: 4px solid;
                }
                
                .result-ok {
                    border-left-color: #28a745;
                }
                
                .result-fail {
                    border-left-color: #dc3545;
                }
                
                .object-name {
                    font-weight: bold;
                    margin-bottom: 5px;
                    font-size: 14px;
                }
                
                .status {
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                
                .status-ok {
                    background-color: #28a745;
                    color: white;
                }
                
                .status-fail {
                    background-color: #dc3545;
                    color: white;
                }
                
                .standard {
                    color: #666;
                    font-size: 11px;
                    margin-bottom: 5px;
                }
                
                .suggestions {
                    margin-top: 8px;
                    padding-top: 8px;
                    border-top: 1px dashed #ddd;
                }
                
                .suggestion-item {
                    font-size: 11px;
                    margin-bottom: 3px;
                    padding-left: 10px;
                }
                
                .color-legend {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 8px;
                    margin-top: 15px;
                    padding-top: 15px;
                    border-top: 1px solid #ddd;
                }
                
                .color-item {
                    display: flex;
                    align-items: center;
                    margin-bottom: 5px;
                }
                
                .color-box {
                    width: 16px;
                    height: 16px;
                    margin-right: 8px;
                    border: 1px solid #666;
                }
                
                .color-label {
                    font-size: 11px;
                }
            </style>
        </head>
        <body>
            <div id="legend-container">
                <div class="legend-header">
                    <div class="legend-title">Анализ доступности</div>
                    <button class="toggle-btn" onclick="toggleLegend()">Свернуть</button>
                </div>
        '''
        
        # Статусы с цветами
        status_config = {
            True: {'text': 'СОБЛЮДАЕТСЯ', 'class': 'status-ok'},
            False: {'text': 'НАРУШЕНО', 'class': 'status-fail'}
        }
        
        # Названия объектов и нормативы
        object_config = {
            'kindergarten': {
                'name': 'Детский сад',
                'standard': '500 м пешком',
                'color': '#FFD700'
            },
            'school': {
                'name': 'Школа',
                'standard': '500 м пешком ИЛИ 15 мин транспортом',
                'color': '#1E90FF'
            },
            'hospital': {
                'name': 'Фельдшерско-акушерский пункт',
                'standard': '2000 м пешком',
                'color': '#DC143C'
            }
        }
        
        # Добавляем результаты для каждого объекта
        for obj_type, config in object_config.items():
            data = final_result.get(obj_type, {})
            is_ok = data.get('ok', False)
            status = status_config[is_ok]
            
            result_class = 'result-ok' if is_ok else 'result-fail'
            
            legend_html += f'''
            <div class="result-item {result_class}">
                <div class="object-name">{config['name']}</div>
                <div class="status {status['class']}">{status['text']}</div>
                <div class="standard">Норматив: {config['standard']}</div>
            '''
            
            # Добавляем информацию о предложениях, если норматив нарушен
            if not is_ok and data.get('suggestions'):
                suggestions = data['suggestions']
                sites = suggestions.get('recommended_sites', [])
                
                if sites:
                    legend_html += '''
                    <div class="suggestions">
                        <div><b>Предложено мест:</b> {}</div>
                    '''.format(len(sites))
                    
                    for i, (lon, lat) in enumerate(sites[:3], 1):  # Показываем первые 3
                        legend_html += f'''
                        <div class="suggestion-item">
                            {i}. Широта: {lat:.5f}, Долгота: {lon:.5f}
                        </div>
                        '''
                    
                    if len(sites) > 3:
                        legend_html += f'''
                        <div class="suggestion-item">
                            ... и еще {len(sites) - 3} вариантов
                        </div>
                        '''
                    
                    criteria = suggestions.get('criteria_used', [])
                    if criteria:
                        legend_html += f'''
                        <div class="suggestion-item">
                            <b>Критерии:</b> {', '.join(criteria)}
                        </div>
                        '''
                    
                    legend_html += '</div>'
            
            legend_html += '</div>'
        
        # Добавляем цветовую легенду
        legend_html += '''
        <div class="color-legend">
            <div class="color-item">
                <div class="color-box" style="background-color: #228B22;"></div>
                <div class="color-label">Жилой дом</div>
            </div>
            <div class="color-item">
                <div class="color-box" style="background-color: #8A2BE2;"></div>
                <div class="color-label">Инфраструктура</div>
            </div>
            <div class="color-item">
                <div class="color-box" style="background-color: #FFD700;"></div>
                <div class="color-label">Детский сад</div>
            </div>
            <div class="color-item">
                <div class="color-box" style="background-color: #1E90FF;"></div>
                <div class="color-label">Школа</div>
            </div>
            <div class="color-item">
                <div class="color-box" style="background-color: #DC143C;"></div>
                <div class="color-label">ФАП</div>
            </div>
            <div class="color-item">
                <div class="color-box" style="background-color: #FF4500;"></div>
                <div class="color-label">Предложения</div>
            </div>
        </div>
        '''
        
        # Закрываем HTML и добавляем JavaScript
        legend_html += '''
        </div>
        
        <script>
        function toggleLegend() {
            var container = document.getElementById('legend-container');
            var button = document.querySelector('.toggle-btn');
            
            if (container.classList.contains('collapsed')) {
                container.classList.remove('collapsed');
                button.textContent = 'Свернуть';
            } else {
                container.classList.add('collapsed');
                button.textContent = 'Развернуть';
            }
        }
        </script>
        </body>
        </html>
        '''
        
        # Добавляем легенду на карту
        m.get_root().html.add_child(folium.Element(legend_html))
    
    def add_custom_css(self, m: folium.Map) -> None:
        """
        Добавляет пользовательские CSS стили на карту
        """
        custom_css = '''
        <style>
            /* Стили для маркеров предложений */
            .suggestion-icon {
                background: none !important;
                border: none !important;
            }
            
            /* Стили для всплывающих окон */
            .leaflet-popup-content {
                font-family: Arial, sans-serif;
                max-height: 300px;
                overflow-y: auto;
            }
            
            /* Стили для контрола слоев */
            .leaflet-control-layers {
                background-color: white;
                border-radius: 5px;
                padding: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            }
            
            /* Стили для легенды скролла */
            #legend-container::-webkit-scrollbar {
                width: 8px;
            }
            
            #legend-container::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 4px;
            }
            
            #legend-container::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 4px;
            }
            
            #legend-container::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
        </style>
        '''
        
        m.get_root().html.add_child(folium.Element(custom_css))
    
    def visualize_accessibility(self, coord: Tuple[float, float], house_id: str = "test_001", save_html: bool = True) -> Tuple[folium.Map, Dict[str, Any]]:
        """
        Основная функция для визуализации анализа доступности
        
        Args:
            coord: координаты для анализа (долгота, широта)
            house_id: идентификатор дома
            save_html: сохранять ли карту в HTML файл
            
        Returns:
            Кортеж (карта, результаты анализа)
        """
        print("=" * 60)
        print("НАЧАЛО АНАЛИЗА ДОСТУПНОСТИ")
        print("=" * 60)
        
        # 1. Проверяем доступность
        print("\n[1/6] Проверка нормативов доступности...")
        accessibility_result = analyze_accessibility(coord)
        
        # 2. Генерируем рекомендации
        print("[2/6] Генерация рекомендаций по размещению...")
        final_result = generate_placement_suggestions(accessibility_result)
        
        # 3. Загружаем данные об инфраструктуре
        print("[3/6] Загрузка данных об инфраструктуре...")
        infrastructure_gdf = self.load_infrastructure_data()
        
        # 4. Создаем базовую карту
        print("[4/6] Создание интерактивной карты...")
        center_coords = (coord[1], coord[0])  # Преобразуем к (lat, lon)
        m = self.create_base_map(center_coords, zoom_start=15)
        
        # 5. Добавляем пользовательские CSS
        self.add_custom_css(m)
        
        # 6. Добавляем жилой дом
        self.add_residential_point(m, coord, house_id)
        
        # 7. Добавляем существующую инфраструктуру
        if not infrastructure_gdf.empty:
            self.add_infrastructure_points(m, infrastructure_gdf)
        
        # 8. Добавляем изохронные зоны
        self.add_isochrones(m, accessibility_result)
        
        # 9. Добавляем предложения по размещению
        self.add_placement_suggestions(m, final_result)
        
        # 10. Добавляем легенду
        self.add_legend(m, final_result)
        
        # 11. Добавляем слой управления
        folium.LayerControl(collapsed=False).add_to(m)
        
        # 12. Сохраняем карту
        if save_html:
            filename = f"accessibility_analysis_{house_id}.html"
            filepath = os.path.join(self.output_dir, filename)
            m.save(filepath)
            print(f"\n[5/6] Карта сохранена: {filepath}")
            
            # Открываем в браузере
            import webbrowser
            webbrowser.open(f'file://{os.path.abspath(filepath)}')
        
        # 13. Создаем текстовый отчет
        print("[6/6] Формирование отчета...")
        report = self.create_summary_report(final_result, coord)
        
        print("\n" + "=" * 60)
        print("АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!")
        print("=" * 60)
        
        return m, final_result
    
    def create_summary_report(self, final_result: Dict[str, Any], coord: Tuple[float, float]) -> str:
        """
        Создает текстовый отчет по результатам анализа
        
        Args:
            final_result: результаты анализа
            coord: координаты анализа
            
        Returns:
            Текст отчета
        """
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("ОТЧЕТ О РЕЗУЛЬТАТАХ АНАЛИЗА ПРОСТРАНСТВЕННОЙ ДОСТУПНОСТИ")
        report_lines.append("=" * 70)
        report_lines.append(f"Дата анализа: {os.path.basename(__file__)}")
        report_lines.append(f"Координаты точки анализа: {coord[1]:.5f}°N, {coord[0]:.5f}°E")
        report_lines.append("-" * 70)
        
        # Статистика по объектам
        object_names = {
            'kindergarten': 'Детский сад',
            'school': 'Школа',
            'hospital': 'Фельдшерско-акушерский пункт (ФАП)'
        }
        
        standards = {
            'kindergarten': 'Пешая доступность 500 метров',
            'school': 'Пешая доступность 500 метров ИЛИ транспортная 15 минут',
            'hospital': 'Пешая доступность 2000 метров'
        }
        
        violations_count = 0
        suggestions_count = 0
        
        for obj_type in ['kindergarten', 'school', 'hospital']:
            data = final_result.get(obj_type, {})
            is_ok = data.get('ok', False)
            
            report_lines.append(f"\n{object_names[obj_type].upper()}")
            report_lines.append(f"Норматив: {standards[obj_type]}")
            report_lines.append(f"Статус: {'СОБЛЮДАЕТСЯ' if is_ok else 'НАРУШЕНО'}")
            
            if not is_ok:
                violations_count += 1
                suggestions = data.get('suggestions', {})
                sites = suggestions.get('recommended_sites', [])
                
                if sites:
                    suggestions_count += len(sites)
                    report_lines.append(f"Предложено вариантов размещения: {len(sites)}")
                    report_lines.append("Координаты предложенных мест:")
                    
                    for i, (lon, lat) in enumerate(sites, 1):
                        report_lines.append(f"  {i:2d}. {lat:.5f}°N, {lon:.5f}°E")
                
                criteria = suggestions.get('criteria_used', [])
                if criteria:
                    report_lines.append(f"Критерии поиска: {', '.join(criteria)}")
        
        # Итоговый вывод
        report_lines.append("\n" + "-" * 70)
        report_lines.append("ИТОГИ:")
        report_lines.append(f"Всего проверено нормативов: 3")
        report_lines.append(f"Нарушено нормативов: {violations_count}")
        report_lines.append(f"Предложено мест для размещения: {suggestions_count}")
        
        if violations_count > 0:
            report_lines.append("\nРЕКОМЕНДАЦИИ:")
            report_lines.append("1. Рассмотреть предложенные координаты для планирования новых объектов")
            report_lines.append("2. Провести дополнительный анализ транспортной доступности")
            report_lines.append("3. Учесть плотность населения при выборе места размещения")
        else:
            report_lines.append("\nВсе нормативы соблюдены. Дополнительные меры не требуются.")
        
        report_lines.append("=" * 70)
        
        report_text = "\n".join(report_lines)
        
        # Сохраняем отчет в файл
        report_file = os.path.join(self.output_dir, "accessibility_analysis_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        # Выводим отчет в консоль
        print(report_text)
        print(f"\nПолный отчет сохранен в файл: {report_file}")
        
        return report_text


def main():
    """
    Основная функция запуска анализа и визуализации
    """
    print("\n" + "="*60)
    print("ГЕОИНФОРМАЦИОННЫЙ АНАЛИЗ ДОСТУПНОСТИ СОЦИАЛЬНОЙ ИНФРАСТРУКТУРЫ")
    print("="*60)
    
    # Примеры координат для тестирования
    test_coordinates = [
        # (долгота, широта), описание
        (( 31.03729335, 60.08477645), "1"),
        ((29.4389616, 60.3551851), "2"),
        ((41.823780357440796, 63.508062172099429), "3"),
    ]
    
    print("\nДоступные тестовые координаты:")
    for i, (coord, desc) in enumerate(test_coordinates, 1):
        print(f"{i}. {desc}: {coord[1]:.3f}°N, {coord[0]:.3f}°E")
    
    try:
        # Выбираем координаты для анализа
        choice = int(input("\nВыберите номер тестовых координат (1-4): ")) - 1
        
        if 0 <= choice < len(test_coordinates):
            selected_coord, description = test_coordinates[choice]
            
            print(f"\nВыбраны координаты: {description}")
            print(f"Долгота: {selected_coord[0]:.5f}, Широта: {selected_coord[1]:.5f}")
            
            # Запрашиваем ID дома
            house_id = input("Введите ID жилого дома (или нажмите Enter для значения по умолчанию): ").strip()
            if not house_id:
                house_id = f"house_{choice+1:03d}"
            
            # Создаем визуализатор и запускаем анализ
            visualizer = AccessibilityVisualizer()
            
            map_obj, results = visualizer.visualize_accessibility(
                coord=selected_coord,
                house_id=house_id,
                save_html=True
            )
            
            print("\n" + "="*60)
            print("Карта успешно создана и открыта в браузере!")
            print("="*60)
            
        else:
            print("Неверный выбор. Завершение программы.")
            
    except ValueError:
        print("Ошибка ввода. Пожалуйста, введите число от 1 до 4.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()