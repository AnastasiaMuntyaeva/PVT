from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
import os
import json
import numpy as np


class MapWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Создаем WebView
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # Определяем путь к HTML файлу
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.html_path = os.path.join(current_dir, 'map.html')

        # Проверяем существование файла
        if not os.path.exists(self.html_path):
            print(f"ОШИБКА: Файл map.html не найден по пути: {self.html_path}")
            # Создаем простую HTML страницу с картой
            self.create_default_html()

        # Загружаем карту
        self.load_map()

        self.track_points = []

    def create_default_html(self):
        """Создает HTML файл с картой, если он отсутствует"""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Track Map</title>
    <meta charset="utf-8" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { margin: 0; padding: 0; }
        #map { width: 100vw; height: 100vh; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        // Инициализация карты
        var map = L.map('map').setView([55.7558, 37.6176], 10);

        // Добавляем тайлы OpenStreetMap
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        // Создаем слои для трека и маркера
        window.trackLayer = L.layerGroup().addTo(map);
        window.markerLayer = L.layerGroup().addTo(map);

        // Маркер (пока пустой)
        window.marker = null;

        // Функция для загрузки трека
        window.loadTrack = function(points) {
            window.trackLayer.clearLayers();

            if (!points || points.length === 0) return;

            var latlngs = points.map(p => [p.lat, p.lon]);

            // Рисуем линию трека
            var polyline = L.polyline(latlngs, {
                color: 'red',
                weight: 3,
                opacity: 0.8
            }).addTo(window.trackLayer);

            // Добавляем точки
            points.forEach((point, index) => {
                var circle = L.circleMarker([point.lat, point.lon], {
                    radius: 3,
                    color: 'blue',
                    fillColor: '#00f',
                    fillOpacity: 0.8
                }).addTo(window.trackLayer);
            });

            // Центрируем карту на треке
            map.fitBounds(polyline.getBounds());
        };

        // Функция для обновления маркера
        window.updateMarker = function(lat, lon, angle) {
            // Удаляем старый маркер
            window.markerLayer.clearLayers();

            if (lat && lon) {
                // Создаем иконку с направлением
                var markerIcon = L.divIcon({
                    className: 'direction-marker',
                    html: `<div style="
                        width: 24px;
                        height: 24px;
                        background-color: #ff4444;
                        border: 3px solid white;
                        border-radius: 50%;
                        transform: rotate(${angle || 0}deg);
                        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                        transition: transform 0.3s ease;
                    "></div>`,
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                });

                window.marker = L.marker([lat, lon], {
                    icon: markerIcon,
                    zIndexOffset: 1000
                }).addTo(window.markerLayer);
            }
        };

        // Функция для очистки трека
        window.clearTrack = function() {
            window.trackLayer.clearLayers();
            window.markerLayer.clearLayers();
            window.marker = null;
        };
    </script>
</body>
</html>"""

        try:
            with open(self.html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ Создан файл map.html по пути: {self.html_path}")
        except Exception as e:
            print(f"❌ Ошибка при создании map.html: {e}")

    def load_map(self):
        """Загружает карту в WebView"""
        try:
            # Конвертируем путь в URL
            url = QUrl.fromLocalFile(self.html_path)
            self.web_view.setUrl(url)
            print(f"✅ Карта загружена из: {self.html_path}")

            # Ждем загрузки страницы
            self.web_view.loadFinished.connect(self.on_load_finished)

        except Exception as e:
            print(f"❌ Ошибка при загрузке карты: {e}")

    def on_load_finished(self, ok):
        """Вызывается после загрузки страницы"""
        if ok:
            print("✅ Страница карты загружена успешно")
            # Если есть точки трека, загружаем их
            if self.track_points:
                self.load_track(self.track_points)
        else:
            print("❌ Ошибка загрузки страницы карты")

    def load_track(self, track_points):
        """Загружает трек на карту"""
        if not track_points:
            return

        self.track_points = track_points

        # Конвертируем точки в JSON для передачи в JavaScript
        points_json = json.dumps(track_points)

        # Вызываем JavaScript функцию для загрузки трека
        js_code = f"""
        try {{
            var points = {points_json};
            if (window.loadTrack) {{
                window.loadTrack(points);
                console.log('Трек загружен, точек: ' + points.length);
            }} else {{
                console.error('Функция loadTrack не найдена');
            }}
        }} catch(e) {{
            console.error('Ошибка при загрузке трека:', e);
        }}
        """

        self.web_view.page().runJavaScript(js_code)
        print(f"✅ Трек загружен на карту: {len(track_points)} точек")

    def update_marker(self, lat, lon, angle=0):
        """Обновляет позицию маркера"""
        js_code = f"""
        try {{
            if (window.updateMarker) {{
                window.updateMarker({lat}, {lon}, {angle});
                console.log('Маркер обновлен: ' + {lat} + ', ' + {lon});
            }}
        }} catch(e) {{
            console.error('Ошибка при обновлении маркера:', e);
        }}
        """

        self.web_view.page().runJavaScript(js_code)

    def clear_track(self):
        """Очищает трек с карты"""
        js_code = """
        try {
            if (window.clearTrack) {
                window.clearTrack();
                console.log('Трек очищен');
            }
        } catch(e) {
            console.error('Ошибка при очистке трека:', e);
        }
        """

        self.web_view.page().runJavaScript(js_code)
        print("🧹 Трек очищен с карты")