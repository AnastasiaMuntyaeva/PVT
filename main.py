import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget, QHBoxLayout, \
    QMessageBox
import folium
from PySide6.QtCore import Qt

from gui.video_player import VideoPlayer
from gui.map_widget import MapWidget
from data_processing.track_loader import load_gpx
from data_processing.video_gps import extract_gpx_from_video


class PanoramicVideoTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Panoramic Video Tracker")
        self.setGeometry(100, 100, 1600, 900)  # Увеличенный размер для панорамы

        # Атрибут для хранения точек трека
        self.track_points = None

        # Основной виджет и layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()  # Основной вертикальный layout для кнопок и контента
        central_widget.setLayout(main_layout)

        # Верхняя панель с кнопками
        button_layout = QHBoxLayout()

        # Кнопки
        self.btn_open_video = QPushButton("📹 Open Video")
        self.btn_open_track = QPushButton("🗺️ Open Track")
        self.btn_extract = QPushButton("📍 Extract track from video")
        self.btn_screenshot = QPushButton("📸 Take Screenshot")

        # Устанавливаем минимальную ширину кнопок
        for btn in [self.btn_open_video, self.btn_open_track, self.btn_extract, self.btn_screenshot]:
            btn.setMinimumHeight(30)

        button_layout.addWidget(self.btn_open_video)
        button_layout.addWidget(self.btn_open_track)
        button_layout.addWidget(self.btn_extract)
        button_layout.addWidget(self.btn_screenshot)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        # Горизонтальный layout для видео и карты
        content_layout = QHBoxLayout()

        # Видео плеер (слева) - больше пространства для панорамы
        self.video_player = VideoPlayer()
        content_layout.addWidget(self.video_player, 3)  # Видео получает 3/4 ширины

        # Карта (справа)
        self.map_widget = MapWidget()
        content_layout.addWidget(self.map_widget, 1)  # Карта получает 1/4 ширины

        main_layout.addLayout(content_layout)

        # Подключение сигналов
        self.btn_open_video.clicked.connect(self.open_video)
        self.btn_open_track.clicked.connect(self.open_track)
        self.btn_extract.clicked.connect(self.extract_track)
        self.btn_screenshot.clicked.connect(self.video_player.take_screenshot)

    def open_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv);;MP4 Files (*.mp4)"
        )
        if file_path:
            print(f"\n=== ОТКРЫТИЕ ВИДЕО ===")
            print(f"Выбран файл: {file_path}")

            # Загружаем видео
            self.video_player.load_video(file_path)

            # Проверяем, что путь сохранился
            print(f"Проверка после загрузки:")
            print(f"video_player.video_path: {self.video_player.video_path}")
            print(f"video_player.is_video_loaded(): {self.video_player.is_video_loaded()}")

            # Подключаем сигнал
            self.video_player.video_frame_changed.connect(self.update_marker)

            # Активируем кнопку извлечения
            self.btn_extract.setEnabled(True)

            print(f"=== ОТКРЫТИЕ ЗАВЕРШЕНО ===\n")

    def open_track(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open GPX Track",
            "",
            "GPX Files (*.gpx)"
        )
        if not file_path:
            return

        print(f"📂 Загружаем трек: {file_path}")
        self.track_points = load_gpx(file_path)
        self.map_widget.load_track(self.track_points)
        print(f"✅ Загружено {len(self.track_points)} точек трека")

        # Добавляем переменную для ручной подстройки
        self.manual_offset = 0  # Будем накапливать ручную подстройку

        # Анализируем трек для определения начала движения
        if self.track_points:
            first_time = self.track_points[0]["time"]
            last_time = self.track_points[-1]["time"]

            print(f"⏱️ Диапазон времени в треке:")
            print(f"   Первая точка: {first_time} (сек: {self.track_points[0]['sec']})")
            print(f"   Последняя точка: {last_time} (сек: {self.track_points[-1]['sec']})")

            # Находим момент, когда начинается реальное движение
            start_lat = self.track_points[0]['lat']
            start_lon = self.track_points[0]['lon']

            movement_start_time = None
            movement_start_index = 0

            for i, point in enumerate(self.track_points):
                lat_diff = abs(point['lat'] - start_lat)
                lon_diff = abs(point['lon'] - start_lon)

                if lat_diff > 0.00001 or lon_diff > 0.00001:
                    movement_start_time = point['sec']
                    movement_start_index = i
                    break

            if movement_start_time is not None:
                print(f"\n🚗 Анализ движения:")
                print(f"   Начальная позиция: ({start_lat:.6f}, {start_lon:.6f})")
                print(f"   Движение начинается с точки {movement_start_index}")
                print(f"   Время начала движения: {movement_start_time} сек")
                print(f"   Статичных точек в начале: {movement_start_index}")

                # Сохраняем базовое смещение
                self.base_time_offset = -movement_start_time
                self.time_offset = self.base_time_offset + self.manual_offset

                print(f"\n🔄 Синхронизация видео и трека:")
                print(f"   Видео начинается с 0 сек")
                print(f"   Движение в треке начинается с {movement_start_time} сек")
                print(f"   Базовое смещение: {self.base_time_offset} сек")
                print(f"   Ручная подстройка: {self.manual_offset} сек")
                print(f"   Итоговое смещение: {self.time_offset} сек")
                print(f"   -> Движение начнется при времени видео {movement_start_time} сек")
            else:
                self.base_time_offset = -self.track_points[0]["sec"]
                self.time_offset = self.base_time_offset
                print("⚠️ Движение не обнаружено в треке!")

            # Добавляем клавиши для подстройки
            print("\n🎮 Для подстройки синхронизации используйте:")
            print("   Клавиши '+' и '-' для сдвига вперед/назад")
            print("   Текущее смещение: 0 сек")

    # Добавьте этот метод для ручной подстройки
    def adjust_sync(self, delta):
        """Ручная подстройка синхронизации"""
        self.manual_offset += delta
        self.time_offset = self.base_time_offset + self.manual_offset
        print(f"⚡ Синхронизация скорректирована: {self.manual_offset:+.1f} сек (итог: {self.time_offset:.1f} сек)")

        # Обновляем маркер для текущего кадра
        if hasattr(self.video_player, 'get_current_time'):
            current_time = self.video_player.get_current_time()
            self.update_marker(current_time)

    # Добавьте обработку клавиш в класс PanoramicVideoTracker
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш для подстройки синхронизации"""
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.adjust_sync(0.5)  # Сдвиг на 0.5 сек вперед
        elif event.key() == Qt.Key_Minus:
            self.adjust_sync(-0.5)  # Сдвиг на 0.5 сек назад
        else:
            super().keyPressEvent(event)

    def extract_track(self):
        """Извлечение GPS-трека из видео"""
        print("\n=== ИЗВЛЕЧЕНИЕ ТРЕКА ===")

        # Проверяем через метод is_video_loaded()
        if not hasattr(self.video_player, 'is_video_loaded'):
            print("❌ Ошибка: video_player не имеет метода is_video_loaded")
            QMessageBox.critical(self, "Ошибка", "Ошибка в модуле video_player")
            return

        if not self.video_player.is_video_loaded():
            print("❌ Видео не загружено")
            print(f"self.video_player.video_path: {getattr(self.video_player, 'video_path', 'None')}")
            print(f"self.video_player.video_loaded: {getattr(self.video_player, 'video_loaded', 'None')}")

            QMessageBox.warning(
                self,
                "Предупреждение",
                "Сначала откройте видео файл!\n\n"
                "Используйте кнопку 'Open Video' для загрузки видео."
            )
            return

        video_path = self.video_player.video_path
        print(f"Путь к видео из video_player: {video_path}")

        # Дополнительная проверка существования файла
        if not video_path or not os.path.exists(video_path):
            print(f"❌ Файл не найден: {video_path}")
            QMessageBox.critical(self, "Ошибка", "Видео файл не найден на диске!")
            return

        print(f"🔄 Извлечение GPS из видео: {os.path.basename(video_path)}")

        # Обновляем статус
        self.statusBar().showMessage("Извлечение GPS трека...")
        self.btn_extract.setEnabled(False)
        self.btn_extract.setText("⏳ Извлечение...")

        try:
            # Извлекаем GPX из видео
            gpx_path = extract_gpx_from_video(video_path)

            if gpx_path and os.path.exists(gpx_path):
                print(f"✅ Трек успешно извлечён: {gpx_path}")

                # Загружаем извлеченный трек
                self.track_points = load_gpx(gpx_path)
                if self.track_points:
                    self.map_widget.load_track(self.track_points)

                    # Показываем информацию о треке
                    msg = f"✅ Загружено точек: {len(self.track_points)}\n"
                    msg += f"🕒 Первая: {self.track_points[0]['time']}\n"
                    msg += f"🕒 Последняя: {self.track_points[-1]['time']}"

                    print(msg)
                    self.statusBar().showMessage(f"Трек загружен: {len(self.track_points)} точек")

                    QMessageBox.information(self, "Успех", f"Трек извлечен!\n{msg}")
                else:
                    print("❌ Не удалось загрузить точки трека")
                    self.statusBar().showMessage("Ошибка загрузки трека")
            else:
                print("❌ GPS данные не найдены в видео")
                self.statusBar().showMessage("GPS не найден в видео")
                QMessageBox.warning(self, "Предупреждение",
                                    "GPS данные не найдены в видео.\n"
                                    "Убедитесь, что видео содержит метаданные с координатами.")

        except Exception as e:
            print(f"❌ Ошибка при извлечении GPS: {e}")
            import traceback
            traceback.print_exc()  # Печатаем полный стек ошибки
            self.statusBar().showMessage(f"Ошибка: {str(e)[:50]}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось извлечь GPS:\n{str(e)}")

        finally:
            # Восстанавливаем кнопку
            self.btn_extract.setEnabled(True)
            self.btn_extract.setText("📍 Extract track from video")
            print("=== ИЗВЛЕЧЕНИЕ ЗАВЕРШЕНО ===\n")

    def update_marker(self, frame_time):
        """Обновление маркера на карте при смене кадра"""
        if not self.track_points:
            return

        try:
            # Находим ближайшую точку к времени видео
            point = min(
                self.track_points,
                key=lambda p: abs(p["sec"] - frame_time)
            )

            lat = point["lat"]
            lon = point["lon"]

            # Обновляем маркер на карте
            self.map_widget.update_marker(lat, lon)

        except Exception as e:
            if frame_time % 10 < 0.1:
                print(f"⚠️ Ошибка обновления маркера: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Устанавливаем стиль
    app.setStyle('Fusion')

    # Создаем и показываем окно
    window = PanoramicVideoTracker()
    window.show()

    # Используем exec() вместо exec_()
    sys.exit(app.exec())