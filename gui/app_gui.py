# app_gui.py
import os
from PySide6.QtWidgets import (QMainWindow, QPushButton, QFileDialog, QVBoxLayout,
                               QWidget, QHBoxLayout, QMessageBox, QProgressDialog, QApplication)
from PySide6.QtCore import Qt
from .video_player import VideoPlayer
from .map_widget import MapWidget
# Предполагаем, что эти модули у вас есть в проекте:
from data_processing.track_processing import TrackExtractionThread, load_track_from_gpx


class PanoramicVideoTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Panoramic Video Tracker")
        self.setGeometry(100, 100, 1600, 900)

        # --- Атрибуты ---
        self.track = None  # Объект трека с данными
        self.video_path = None

        # --- Виджеты ---
        self.video_player = VideoPlayer()
        self.map_widget = MapWidget()

        # --- Кнопки ---
        self.btn_open_video = QPushButton("📹 Open Video")
        self.btn_open_video.setMinimumHeight(30)

        # --- Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.btn_open_video)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        content_layout = QHBoxLayout()
        content_layout.addWidget(self.video_player, 3)
        content_layout.addWidget(self.map_widget, 1)
        main_layout.addLayout(content_layout, 1)

        # --- Сигналы (Вместо Таймера) ---
        self.btn_open_video.clicked.connect(self.open_video)
        # Соединяем сигнал изменения кадра из плеера с обновлением маркера
        self.video_player.video_frame_changed.connect(self.update_marker)

    # ---------------- Открытие видео ----------------
    def open_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        if file_path:
            self.video_path = file_path
            self.video_player.load_video(file_path)
            # После загрузки видео начинаем извлекать GPS
            self.start_gps_extraction(file_path)

    # ---------------- Извлечение GPS (Поток) ----------------
    def start_gps_extraction(self, video_path):
        # Создаем окно прогресса
        self.progress = QProgressDialog("Извлечение GPS данных...", "Отмена", 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.show()

        # Запускаем фоновый поток, чтобы GUI не «фризил»
        self.extraction_thread = TrackExtractionThread(video_path)
        self.extraction_thread.finished.connect(self.on_gps_ready)
        self.extraction_thread.error.connect(self.on_gps_error)
        self.extraction_thread.start()

    def on_gps_ready(self, gpx_path):
        self.progress.close()
        try:
            # Загружаем данные из временного GPX файла
            self.track = load_track_from_gpx(gpx_path)
            # Рисуем линию трека на карте
            self.map_widget.load_track(self.track.points)
            self.statusBar().showMessage(f"GPS загружен: {len(self.track.points)} точек")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось обработать GPS: {e}")

    def on_gps_error(self, message):
        self.progress.close()
        QMessageBox.warning(self, "GPS", f"Данные GPS не найдены в видео: {message}")

    # ---------------- Обновление маркера ----------------
    def update_marker(self, frame_time):
        """Вызывается автоматически при каждом новом кадре видео"""
        if not self.track:
            return

        # Получаем интерполированные координаты для текущей секунды видео
        lat, lon, angle, speed = self.track.get_interpolated_data(frame_time)

        if lat is not None and lon is not None:
            # Обновляем положение иконки на карте
            self.map_widget.update_marker(lat, lon, angle)