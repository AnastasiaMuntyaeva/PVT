import subprocess
from datetime import datetime, timedelta
import gpxpy
import gpxpy.gpx
import sys
from pathlib import Path
import re

LRV_FILE = "Р-351, км 300-317.mp4"
OUTPUT_GPX = "track.gpx"

def run_exiftool(lrv_path: str):
    script_dir = Path(__file__).resolve().parent
    exiftool_path = script_dir / "exiftool.exe"
    fmt_path = script_dir / "gps.fmt"

    if not exiftool_path.exists():
        raise FileNotFoundError(f"❌ exiftool.exe не найден: {exiftool_path}")

    if not fmt_path.exists():
        raise FileNotFoundError(f"❌ gps.fmt не найден: {fmt_path}")

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

    print("🔍 Вывод exiftool:")
    print(result.stdout)  # Добавим вывод, чтобы понять, что возвращает exiftool

    return result.stdout.splitlines()


def dms_to_decimal(dms_str: str) -> float:
    """
    Преобразует строку вида:
    56 deg 44' 59.70" N
    в десятичные градусы
    """
    pattern = r'(\d+)\s+deg\s+(\d+)\'\s+([\d.]+)"\s+([NSEW])'
    match = re.match(pattern, dms_str)

    if not match:
        raise ValueError(f"Не удалось распарсить координату: {dms_str}")

    deg, minutes, seconds, direction = match.groups()

    decimal = float(deg) + float(minutes) / 60 + float(seconds) / 3600

    if direction in ['S', 'W']:
        decimal *= -1

    return decimal

def extract_gps_points(lines):
    points = []
    last_point = None  # отслеживаем последнюю добавленную точку

    for line in lines:
        if not line.strip():
            continue

        try:
            sample_time, coords = line.split(",", 1)

            # Используем регулярное выражение для извлечения времени в формате "часы:минуты:секунды"
            time_match = re.match(r'(\d+):(\d+):(\d+)', sample_time)
            if not time_match:
                continue  # Если формат времени не совпадает, пропускаем строку

            # Преобразуем время в секунды
            hours, minutes, seconds = map(int, time_match.groups())
            total_seconds = hours * 3600 + minutes * 60 + seconds

            lat_str, lon_str = coords.split(",")  # разделяем координаты

            if not lat_str or not lon_str:
                continue

            lat = dms_to_decimal(lat_str)
            lon = dms_to_decimal(lon_str)

            timestamp = datetime(1970, 1, 1) + timedelta(seconds=total_seconds)

            # Пропускаем одинаковые точки
            if last_point and lat == last_point[0] and lon == last_point[1] and timestamp == last_point[2]:
                continue  # пропускаем точку, если она такая же, как предыдущая

            points.append((lat, lon, timestamp))
            last_point = (lat, lon, timestamp)  # обновляем последнюю точку

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

def main():
    lrv_path = Path(LRV_FILE)

    if not lrv_path.exists():
        print(f"❌ Файл не найден: {LRV_FILE}")
        sys.exit(1)

    print("📡 Читаю GPS из LRV через exiftool...")
    exif_data = run_exiftool(str(lrv_path))

    print("🧭 Извлекаю точки...")
    points = extract_gps_points(exif_data)

    print(f"✅ Найдено точек: {len(points)}")

    print("💾 Сохраняю GPX...")
    create_gpx(points, OUTPUT_GPX)

    print(f"🎉 Готово: {OUTPUT_GPX}")

if __name__ == "__main__":
    main()
