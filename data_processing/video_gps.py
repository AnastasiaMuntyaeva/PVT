# video_gps
import subprocess
import os
import gpxpy
import gpxpy.gpx
import re
from datetime import datetime, timedelta
from pathlib import Path


def run_exiftool(lrv_path: str):
    script_dir = Path(__file__).resolve().parent
    exiftool_path = script_dir / "exiftool.exe"
    fmt_path = script_dir / "gps.fmt"

    if not exiftool_path.exists():
        raise FileNotFoundError(f"exiftool.exe не найден: {exiftool_path}")

    if not fmt_path.exists():
        raise FileNotFoundError(f"gps.fmt не найден: {fmt_path}")

    cmd = [
        str(exiftool_path),
        "-ee",
        "-api", "LargeFileSupport=1",
        "-p", str(fmt_path),
        str(lrv_path)
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=script_dir
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout.splitlines()


def dms_to_decimal(dms_str: str) -> float:
    pattern = r'(\d+)\s+deg\s+(\d+)\'\s+([\d.]+)"\s+([NSEW])'
    match = re.match(pattern, dms_str)

    if not match:
        raise ValueError(f"Не удалось распарсить координату: {dms_str}")

    deg, minutes, seconds, direction = match.groups()

    decimal = float(deg) + float(minutes) / 60 + float(seconds) / 3600

    if direction in ['S', 'W']:
        decimal *= -1

    return decimal


def extract_gps_points(lines, points_frequency=5):
    points = []
    seen_times = set()
    last_point = None
    time_threshold = timedelta(seconds=1)

    point_counter = 0

    for idx, line in enumerate(lines):
        if not line.strip():
            continue

        try:
            sample_time, coords = line.split(",", 1)

            time_match = re.match(r'(\d+):(\d+):(\d+)', sample_time)
            if not time_match:
                continue

            hours, minutes, seconds = map(int, time_match.groups())
            total_seconds = hours * 3600 + minutes * 60 + seconds

            lat_str, lon_str = coords.split(",")
            if not lat_str or not lon_str:
                continue

            lat = dms_to_decimal(lat_str)
            lon = dms_to_decimal(lon_str)

            timestamp = datetime(1970, 1, 1) + timedelta(seconds=total_seconds)

            lat = round(lat, 6)
            lon = round(lon, 6)

            # Проверка на дубликаты по времени
            time_is_duplicate = False
            for seen_time in seen_times:
                time_diff = abs(timestamp - seen_time)
                if time_diff < time_threshold:
                    time_is_duplicate = True
                    break

            if time_is_duplicate:
                continue

            # Проверка на дубликаты по координатам
            if last_point and lat == last_point[0] and lon == last_point[1]:
                continue

            point_counter += 1

            # Берем каждую points_frequency-ю точку
            if point_counter % points_frequency == 1:
                seen_times.add(timestamp)
                points.append((lat, lon, timestamp))
                last_point = (lat, lon, timestamp)

        except Exception as e:
            print(f"Ошибка при обработке строки: {line}. Ошибка: {e}")
            continue

    return points


def create_gpx(points, output_file):
    if not points:
        raise ValueError("GPS точки не найдены")

    gpx = gpxpy.gpx.GPX()

    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)

    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for lat, lon, ts in points:
        segment.points.append(
            gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon, time=ts)
        )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())


def extract_gpx_from_video(video_path):
    """
    Извлекает GPS-трек из видеофайла с помощью ExifTool
    Сохраняет GPX файл в папку GPX_folder рядом со скриптом
    Возвращает путь к созданному GPX файлу или None
    """
    print(f"\n=== ИЗВЛЕЧЕНИЕ GPS ИЗ ВИДЕО (ExifTool) ===")
    print(f"Видео: {video_path}")

    if not os.path.exists(video_path):
        print(f"Файл не найден: {video_path}")
        return None

    try:
        # Извлекаем данные с помощью ExifTool
        exif_data = run_exiftool(video_path)

        print("Извлекаю точки...")
        points = extract_gps_points(exif_data)

        print(f"Найдено точек: {len(points)}")

        # Создаем папку GPX_folder, если её нет
        script_dir = Path(__file__).resolve().parent
        gpx_folder = script_dir / "GPX_folder"
        gpx_folder.mkdir(exist_ok=True)  # создает папку, если её нет

        print(f"Папка для GPX файлов: {gpx_folder}")

        # Получаем имя видеофайла без пути и расширения
        video_name = os.path.splitext(os.path.basename(video_path))[0]

        # Формируем путь для GPX файла в папке GPX_folder
        gpx_path = gpx_folder / f"{video_name}_extracted.gpx"

        print(f"Создание GPX файла: {gpx_path}")

        # Создаем GPX файл
        create_gpx(points, str(gpx_path))

        print(f"Успешно создан GPX файл с {len(points)} точками")
        print(f"Путь: {gpx_path}")

        return str(gpx_path)

    except Exception as e:
        print(f"Ошибка при извлечении GPS: {e}")
        return None