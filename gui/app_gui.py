import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget, QHBoxLayout, QMessageBox, QProgressDialog
from PySide6.QtCore import Qt
from .video_player import VideoPlayer
from .map_widget import MapWidget
from data_processing.track_processing import TrackExtractionThread, load_track_from_gpx

class PanoramicVideoTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Panoramic Video Tracker")
        self.setGeometry(100, 100, 1600, 900)

        self.track = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Верхняя панель кнопок
        button_layout = QHBoxLayout()
        self.btn_open_video = QPushButton("📹 Open Video")
        self.btn_screenshot = QPushButton("📸 Take Screenshot")
        for btn in [self.btn_open_video, self.btn_screenshot]:
            btn.setMinimumHeight(30)
        button_layout.addWidget(self.btn_open_video)
        button_layout.addWidget(self.btn_screenshot)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Видео и карта
        content_layout = QHBoxLayout()
        self.video_player = VideoPlayer()
        self.map_widget = MapWidget()
        content_layout.addWidget(self.video_player, 3)
        content_layout.addWidget(self.map_widget, 1)
        main_layout.addLayout(content_layout)

        # Сигналы
        self.btn_open_video.clicked.connect(self.open_video)
        self.btn_screenshot.clicked.connect(self.video_player.take_screenshot)
        self.video_player.video_frame_changed.connect(self.update_marker)

        self.statusBar().showMessage("Готов к работе")

    def show_progress_dialog(self, message="Извлечение GPS трека..."):
        self.progress_dialog = QProgressDialog(message, None, 0, 0, self)
        self.progress_dialog.setWindowTitle("Пожалуйста, подождите")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
        QApplication.processEvents()

    def update_progress(self, message):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            QApplication.processEvents()

    def open_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*.*)")
        if not file_path:
            return

        self.video_player.load_video(file_path)
        self.track = None

        try:
            self.map_widget.clear_track()
        except AttributeError:
            pass

        self.extract_track_async()

    def extract_track_async(self):
        if not hasattr(self.video_player, 'is_video_loaded') or not self.video_player.is_video_loaded():
            QMessageBox.warning(self, "Предупреждение", "Сначала откройте видео файл!")
            return

        video_path = self.video_player.video_path
        if not video_path or not os.path.exists(video_path):
            QMessageBox.critical(self, "Ошибка", "Видео файл не найден на диске!")
            return

        self.show_progress_dialog("Начало извлечения GPS данных...")

        self.extraction_thread = TrackExtractionThread(video_path)
        self.extraction_thread.progress.connect(self.update_progress)
        self.extraction_thread.finished.connect(self.on_track_extracted)
        self.extraction_thread.error.connect(self.on_extraction_error)
        self.extraction_thread.start()

    def on_track_extracted(self, gpx_path):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        try:
            self.track = load_track_from_gpx(gpx_path)
            self.map_widget.load_track(self.track.points)
            self.statusBar().showMessage(f"Трек загружен: {len(self.track.points)} точек")
        except Exception as e:
            QMessageBox.warning(self, "Предупреждение", f"Не удалось загрузить трек:\n{str(e)}")

    def on_extraction_error(self, message):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.statusBar().showMessage("❌ Ошибка извлечения GPS")
        QMessageBox.warning(self, "Ошибка извлечения GPS", message)

    def update_marker(self, frame_time):
        if not self.track:
            return

        lat, lon, angle, speed = self.track.get_interpolated_data(frame_time)
        if lat is None:
            return
        self.map_widget.update_marker(lat, lon, angle)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PanoramicVideoTracker()
    window.show()
    sys.exit(app.exec())