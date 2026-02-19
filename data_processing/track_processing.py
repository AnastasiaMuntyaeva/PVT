import os
import math
from PySide6.QtCore import QThread, Signal
from data_processing.track_loader import load_gpx
from data_processing.video_gps import extract_gpx_from_video

class TrackExtractionThread(QThread):
    """Поток для извлечения трека из видео"""
    progress = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path

    def run(self):
        try:
            self.progress.emit("🔄 Извлечение GPS данных из видео...")
            gpx_path = extract_gpx_from_video(self.video_path)

            if gpx_path and os.path.exists(gpx_path):
                self.progress.emit("✅ GPS данные успешно извлечены")
                self.finished.emit(gpx_path)
            else:
                self.error.emit("❌ GPS данные не найдены в видео")
        except Exception as e:
            self.error.emit(f"❌ Ошибка: {str(e)}")


class Track:
    """Модель трека с интерполяцией и синхронизацией"""

    def __init__(self, points):
        self.points = points
        self.time_offset = 0
        self.analyze_sync()

    def analyze_sync(self):
        """Анализ трека для синхронизации с видео"""
        if not self.points:
            return

        first_point = self.points[0]
        start_lat = first_point['lat']
        start_lon = first_point['lon']

        movement_start_time = None

        for i, point in enumerate(self.points):
            lat_diff = abs(point['lat'] - start_lat)
            lon_diff = abs(point['lon'] - start_lon)
            if lat_diff > 0.00001 or lon_diff > 0.00001:
                movement_start_time = point['sec']
                break

        if movement_start_time is not None:
            self.time_offset = -movement_start_time
        else:
            self.time_offset = -first_point['sec']

    def get_interpolated_data(self, frame_time):
        """Получить интерполированные данные для заданного времени кадра"""
        if not self.points:
            return None, None, None, None

        track_time = frame_time + self.time_offset

        points = self.points

        if track_time < points[0]["sec"]:
            return points[0]["lat"], points[0]["lon"], 0, 0

        if track_time > points[-1]["sec"]:
            return points[-1]["lat"], points[-1]["lon"], 0, 0

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]

            if p1["sec"] <= track_time <= p2["sec"]:
                if p2["sec"] - p1["sec"] == 0:
                    return p1["lat"], p1["lon"], 0, 0

                ratio = (track_time - p1["sec"]) / (p2["sec"] - p1["sec"])

                lat = p1["lat"] + ratio * (p2["lat"] - p1["lat"])
                lon = p1["lon"] + ratio * (p2["lon"] - p1["lon"])

                dy = p2["lat"] - p1["lat"]
                dx = p2["lon"] - p1["lon"]
                angle = 0 if abs(dy) < 1e-6 and abs(dx) < 1e-6 else math.degrees(math.atan2(dy, dx))

                speed = p1.get("speed", 0)
                return lat, lon, angle, speed

        return None, None, None, None


def load_track_from_gpx(gpx_path):
    """Загрузить трек из GPX файла и вернуть объект Track"""
    if not os.path.exists(gpx_path):
        raise FileNotFoundError(f"Файл не найден: {gpx_path}")

    points = load_gpx(gpx_path)
    return Track(points)