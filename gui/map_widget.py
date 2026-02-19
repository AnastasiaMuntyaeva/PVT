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

    def update_marker(self, lat, lon):
        """Обновить позицию маркера"""
        if self.map:
            # Удаляем старый маркер
            if self.marker:
                self.marker.remove()

            # Добавляем новый маркер
            self.marker = folium.Marker(
                [lat, lon],
                popup='Current Position',
                icon=folium.Icon(color='red')
            ).add_to(self.map)

            self.update_web_view()