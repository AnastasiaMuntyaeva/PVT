import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QSlider, QLabel, QMessageBox, QSizePolicy
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Signal, Qt, QUrl


class VideoPlayer(QWidget):
    video_frame_changed = Signal(float)

    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.video_path = None
        self.video_loaded = False

        # Настройка макета
        layout = QVBoxLayout()
        self.setLayout(layout)

        # ВАЖНО: Настройка видео виджета для правильного отображения
        self.video_widget.setSizePolicy(
            QSizePolicy.Expanding,  # Растягивается по горизонтали
            QSizePolicy.Expanding  # Растягивается по вертикали
        )

        # Сохраняем пропорции видео (2:1 для 7680x3840)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)  # Сохранять пропорции

        # Минимальный размер для комфортного просмотра
        self.video_widget.setMinimumSize(640, 320)  # Минимум 640x320 (2:1)

        # Видео виджет
        layout.addWidget(self.video_widget)
        self.player.setVideoOutput(self.video_widget)

        # Панель управления
        control_layout = QHBoxLayout()

        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")

        # Изначально кнопки неактивны
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.setEnabled(False)

        self.time_label = QLabel("00:00 / 00:00")

        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.position_slider)
        control_layout.addWidget(self.time_label)

        layout.addLayout(control_layout)

        # Подключение сигналов
        self.play_button.clicked.connect(self.player.play)
        self.pause_button.clicked.connect(self.player.pause)
        self.stop_button.clicked.connect(self.player.stop)

        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.positionChanged.connect(self.emit_frame_time)

        # Подключаем сигнал об ошибках
        self.player.errorOccurred.connect(self.handle_error)

    def load_video(self, file_path):
        """Загрузить видео файл"""
        print(f"\n=== ЗАГРУЗКА ВИДЕО ===")
        print(f"Путь к видео: {file_path}")
        print(f"Файл существует: {os.path.exists(file_path)}")

        # Сохраняем путь
        self.video_path = file_path
        self.video_loaded = True

        print(f"self.video_path установлен в: {self.video_path}")
        print(f"self.video_loaded установлен в: {self.video_loaded}")

        # Загружаем видео в плеер
        url = QUrl.fromLocalFile(file_path)
        print(f"URL для загрузки: {url.toString()}")

        self.player.setSource(url)

        # Активируем кнопки
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.position_slider.setEnabled(True)

        print(f"✅ Видео загружено: {os.path.basename(file_path)}")
        print(f"=== ЗАГРУЗКА ЗАВЕРШЕНА ===\n")

    def get_video_path(self):
        """Метод для получения пути к видео"""
        print(f"DEBUG: get_video_path() вызван, возвращает: {self.video_path}")
        return self.video_path

    def is_video_loaded(self):
        """Проверка, загружено ли видео"""
        return self.video_loaded and self.video_path is not None

    def position_changed(self, position):
        """Обновление позиции слайдера"""
        self.position_slider.setValue(position)

        # Обновление метки времени
        duration = self.player.duration()
        if duration > 0:
            position_secs = position // 1000
            duration_secs = duration // 1000
            self.time_label.setText(
                f"{position_secs // 60:02d}:{position_secs % 60:02d} / {duration_secs // 60:02d}:{duration_secs % 60:02d}")

    def duration_changed(self, duration):
        """Изменение длительности видео"""
        self.position_slider.setRange(0, duration)

    def emit_frame_time(self, position):
        """Отправка сигнала с текущим временем"""
        self.video_frame_changed.emit(position / 1000.0)

    def handle_error(self, error, error_string):
        """Обработка ошибок плеера"""
        print(f"❌ Ошибка плеера: {error_string}")
        QMessageBox.critical(self, "Ошибка видео", f"Не удалось воспроизвести видео:\n{error_string}")

    def take_screenshot(self):
        """Сделать скриншот"""
        if not self.is_video_loaded():
            print("❌ Видео не загружено")
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите видео!")
            return
        print("📸 Функция скриншота будет реализована позже")