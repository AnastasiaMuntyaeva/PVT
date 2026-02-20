import sys
import numpy as np

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel, QGridLayout
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtGui import QImage
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL import GL as gl
from OpenGL.GLU import gluPerspective  # Добавляем этот импорт
import cv2


class PanoramicGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.texture_id = None
        self.setMinimumSize(640, 640)

        # Параметры для управления просмотром
        self.yaw = 220.0  # Поворот по горизонтали (в градусах) - вокруг оси Y
        self.pitch = 0.0  # Поворот по вертикали (в градусах) - вокруг оси X
        self.fov = 75  # Поле зрения в градусах
        self.last_pos = None

    def initializeGL(self):
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glEnable(gl.GL_DEPTH_TEST)
        self.texture_id = gl.glGenTextures(1)

    def resizeGL(self, w, h):
        gl.glViewport(0, 0, w, h)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        aspect = w / h if h != 0 else 1.0
        gluPerspective(self.fov, aspect, 0.1, 100.0)
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        if self.image is None:
            return

        # Загружаем текстуру с панорамным изображением
        img = self.image.convertToFormat(QImage.Format_RGBA8888)
        width = img.width()
        height = img.height()

        ptr = img.constBits()
        byte_array = ptr.tobytes()
        img_data = np.frombuffer(byte_array, dtype=np.uint8).reshape(height, width, 4)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height,
                        0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data)

        # Настраиваем камеру
        gl.glLoadIdentity()

        # Сначала применяем вертикальный поворот (вокруг оси X)
        gl.glRotatef(self.pitch, 1.0, 0.0, 0.0)
        # Затем горизонтальный поворот (вокруг оси Y)
        gl.glRotatef(self.yaw, 0.0, 1.0, 0.0)

        # Рисуем сферу с текстурой (с внутренней стороны)
        self.draw_sphere(64, 64)

    def draw_sphere(self, slices, stacks):
        for i in range(stacks):
            lat0 = np.pi * (-0.5 + float(i) / stacks)
            lat1 = np.pi * (-0.5 + float(i + 1) / stacks)

            y0, r0 = np.sin(lat0), np.cos(lat0)
            y1, r1 = np.sin(lat1), np.cos(lat1)

            gl.glBegin(gl.GL_QUAD_STRIP)
            for j in range(slices + 1):
                lng = 2 * np.pi * float(j) / slices
                x0, z0 = np.cos(lng) * r0, -np.sin(lng) * r0
                x1, z1 = np.cos(lng) * r1, -np.sin(lng) * r1

                u = 1.0 - float(j) / slices  # инвертируем горизонтально
                v0 = 1.0 - float(i) / stacks  # инвертируем вертикально
                v1 = 1.0 - float(i + 1) / stacks

                gl.glTexCoord2f(u, v0)
                gl.glVertex3f(x0, y0, z0)
                gl.glTexCoord2f(u, v1)
                gl.glVertex3f(x1, y1, z1)
            gl.glEnd()

    def set_frame(self, qimage: QImage):
        self.image = qimage
        self.update()

    def mousePressEvent(self, event):
        self.last_pos = event.position()

    def mouseMoveEvent(self, event):
        if self.last_pos is None:
            return

        # Вычисляем дельту движения мыши
        delta = event.position() - self.last_pos

        # Горизонтальное движение мыши -> поворот вокруг вертикальной оси (Y)
        self.yaw += delta.x() * 0.3

        # Вертикальное движение мыши -> поворот вокруг горизонтальной оси (X)
        self.pitch += delta.y() * 0.3

        # Ограничиваем pitch, чтобы не переворачивать изображение
        # Не даем уйти за полюса (от -90 до 90 градусов)
        self.pitch = max(-90.0, min(90.0, self.pitch))

        # Нормализуем yaw для предотвращения накопления ошибок (0-360 градусов)
        self.yaw = self.yaw % 360.0

        self.last_pos = event.position()
        self.update()

    def wheelEvent(self, event):
        # Изменение поля зрения (зум)
        delta = event.angleDelta().y() / 120
        self.fov -= delta * 5
        self.fov = max(30.0, min(120.0, self.fov))

        # Обновляем проекцию
        self.resizeGL(self.width(), self.height())
        self.update()






class VideoPlayer(QWidget):
    video_frame_changed = Signal(float)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Panoramic Video Player")

        # OpenGL виджет для видео
        self.gl_widget = PanoramicGLWidget(self)

        # Кнопки управления видео (маленькие)
        self.play_btn = QPushButton()
        self.play_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_btn.setFixedSize(30, 30)

        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(QIcon.fromTheme("media-playback-pause"))
        self.pause_btn.setFixedSize(30, 30)

        self.reset_btn = QPushButton()
        self.reset_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.reset_btn.setFixedSize(30, 30)

        # Слайдер
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)

        # Метка времени слева
        self.time_label = QLabel("00:00 / 00:00")

        # ---------------- Основной layout ----------------
        main_layout = QVBoxLayout(self)

        main_layout.addWidget(self.gl_widget)
        main_layout.addWidget(self.slider)

        # Нижний layout — одна линия под слайдером
        from PySide6.QtWidgets import QSpacerItem, QSizePolicy

        # Нижний layout
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.time_label, alignment=Qt.AlignLeft)

        # Контейнер с кнопками
        buttons_container = QHBoxLayout()
        buttons_container.addWidget(self.play_btn)
        buttons_container.addWidget(self.pause_btn)
        buttons_container.addWidget(self.reset_btn)
        bottom_layout.addLayout(buttons_container)
        bottom_layout.addStretch(1)  # пустое место справа

        main_layout.addLayout(bottom_layout)

        # ---------------- Видео переменные ----------------
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.fps = 30
        self.total_frames = 0
        self.current_frame = 0
        self.is_playing = False
        self.user_dragging_slider = False

        # ---------------- Сигналы ----------------
        self.play_btn.clicked.connect(self.play_video)
        self.pause_btn.clicked.connect(self.pause_video)
        self.reset_btn.clicked.connect(self.reset_view)
        self.slider.sliderPressed.connect(self.slider_pressed)
        self.slider.sliderReleased.connect(self.slider_released)
        self.slider.sliderMoved.connect(self.slider_moved)
        self.slider.mousePressEvent = self.slider_clicked

    # ---------------- Методы ----------------
    def slider_clicked(self, event):
        if self.cap:
            pos = event.position().x()
            value = int(pos / self.slider.width() * self.slider.maximum())
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, value)
            self.current_frame = value
            self.update_frame(first_frame=True)
        super(QSlider, self.slider).mousePressEvent(event)

    def load_video(self, path):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            print(f"Ошибка: Не удалось открыть видео {path}")
            return
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.slider.setMaximum(self.total_frames - 1)
        self.slider.setEnabled(True)
        self.timer.setInterval(int(1000 / self.fps))
        self.current_frame = 0
        self.update_frame(first_frame=True)

    def update_frame(self, first_frame=False):
        if not self.cap:
            return
        if self.is_playing or first_frame:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                self.display_frame(frame)
            else:
                self.pause_video()
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.current_frame = 0
                ret, frame = self.cap.read()
                if ret:
                    self.display_frame(frame)

        # ---- сигнал для обновления маркера ----
        if self.cap:
            current_sec = self.current_frame / self.fps
            self.video_frame_changed.emit(current_sec)

    def display_frame(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimage = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.gl_widget.set_frame(qimage)

        if not self.user_dragging_slider:
            self.slider.blockSignals(True)
            self.slider.setValue(self.current_frame)
            self.slider.blockSignals(False)

        current_sec = int(self.current_frame / self.fps)
        total_sec = int(self.total_frames / self.fps)
        self.time_label.setText(
            f"{current_sec // 60:02d}:{current_sec % 60:02d} / {total_sec // 60:02d}:{total_sec % 60:02d}"
        )

    def play_video(self):
        if self.cap:
            self.is_playing = True
            self.timer.start()

    def pause_video(self):
        self.is_playing = False
        self.timer.stop()

    def reset_view(self):
        self.gl_widget.yaw = 220.0
        self.gl_widget.pitch = 0.0
        self.gl_widget.fov = 90.0
        self.gl_widget.resizeGL(self.gl_widget.width(), self.gl_widget.height())
        self.gl_widget.update()

    def slider_pressed(self):
        self.user_dragging_slider = True
        self.pause_video()

    def slider_released(self):
        self.user_dragging_slider = False
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.slider.value())
        self.current_frame = self.slider.value()
        self.update_frame(first_frame=True)

    def slider_moved(self, value):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, value)
            self.current_frame = value
            self.update_frame(first_frame=True)