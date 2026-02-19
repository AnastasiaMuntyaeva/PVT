from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
import folium
from PySide6.QtWebEngineWidgets import QWebEngineView
import io
import numpy as np


class MapWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Создаем карту
        self.map = folium.Map(location=[55.7558, 37.6176], zoom_start=10)  # Москва по умолчанию
        self.web_view = QWebEngineView()

        # Сохраняем карту в HTML и загружаем
        self.update_web_view()

        layout.addWidget(self.web_view)

        self.track_line = None
        self.marker = None

    def update_web_view(self):
        """Обновить отображение карты"""
        data = io.BytesIO()
        self.map.save(data, close_file=False)
        self.web_view.setHtml(data.getvalue().decode())

    def load_track(self, track_points):
        """Загрузить трек на карту"""
        if not track_points:
            return

        # Извлекаем координаты
        lats = [p['lat'] for p in track_points]
        lons = [p['lon'] for p in track_points]

        # Центрируем карту на треке
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)
        self.map = folium.Map(location=[center_lat, center_lon], zoom_start=12)

        # Добавляем линию трека
        points = [[p['lat'], p['lon']] for p in track_points]
        self.track_line = folium.PolyLine(points, color='blue', weight=3).add_to(self.map)

        # Добавляем начальную точку
        self.marker = folium.Marker(
            [track_points[0]['lat'], track_points[0]['lon']],
            popup='Start',
            icon=folium.Icon(color='green')
        ).add_to(self.map)

        self.update_web_view()

    def update_marker(self, lat, lon, angle=0, speed=0):
        """
        Обновить позицию маркера на карте

        Args:
            lat: широта
            lon: долгота
            angle: угол направления (в градусах)
            speed: скорость (не используется, но оставляем для совместимости)
        """
        try:
            # JavaScript код для обновления маркера
            js_code = f"""
            if (window.marker) {{
                window.marker.setLatLng([{lat}, {lon}]);

                // Обновляем угол поворота, если нужно
                if (window.marker._icon) {{
                    window.marker._icon.style.transform += ' rotate({angle}deg)';
                }}
            }}
            """
            self.web_view.page().runJavaScript(js_code)
        except Exception as e:
            print(f"Ошибка при обновлении маркера: {e}")

    def clear_track(self):
        """Очистить трек с карты"""
        try:
            self.web_view.page().runJavaScript("window.clearTrack();")
            print("🧹 Трек очищен с карты")
        except Exception as e:
            print(f"Ошибка при очистке трека: {e}")