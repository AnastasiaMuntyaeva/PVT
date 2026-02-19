import subprocess
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta


def extract_gpx_from_video(video_path):
    """
    Извлекает GPS-трек из видеофайла с помощью ExifTool
    Возвращает путь к созданному GPX файлу или None
    """
    print(f"\n=== ИЗВЛЕЧЕНИЕ GPS ИЗ ВИДЕО (ExifTool) ===")
    print(f"Видео: {video_path}")

    # Проверяем существование файла
    if not os.path.exists(video_path):
        print(f"❌ Файл не найден: {video_path}")
        return None

    try:
        # 1. Сначала проверяем, есть ли вообще GPS данные в видео
        print("🔍 Проверка наличия GPS метаданных...")

        check_command = [
            'exiftool',
            '-json',
            '-GPSLatitude',
            '-GPSLongitude',
            '-GPSDateTime',
            '-GPSTimeStamp',
            '-GPSDateStamp',
            '-SampleTime',  # Для временных меток в видео
            '-TimeStamp',
            video_path
        ]

        result = subprocess.run(check_command, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Ошибка ExifTool: {result.stderr}")
            return None

        # Парсим JSON
        metadata_list = json.loads(result.stdout)
        if not metadata_list:
            print("❌ Не удалось получить метаданные")
            return None

        metadata = metadata_list[0]

        # Проверяем наличие GPS координат
        has_gps = any(key.startswith('GPS') for key in metadata.keys())

        if not has_gps:
            print("❌ GPS данные не найдены в видео")
            print("Доступные метаданные:", list(metadata.keys())[:10])
            return None

        print("✅ GPS данные найдены!")

        # 2. Получаем все временные метки и координаты
        print("📊 Извлечение временных меток и координат...")

        # Для разных форматов видео могут быть разные теги
        # Пробуем разные варианты получения временных меток кадров

        # Вариант 1: Если есть SampleTime (для некоторых дронов)
        if 'SampleTime' in metadata:
            print("📹 Используем SampleTime для временных меток")
            # Здесь нужно получить все SampleTime, но ExifTool в JSON режиме
            # показывает только первый. Используем другой подход.

            # Получаем все SampleTime через текстовый вывод
            sample_cmd = ['exiftool', '-SampleTime', '-G0', '-a', video_path]
            sample_result = subprocess.run(sample_cmd, capture_output=True, text=True)

            # Парсим текстовый вывод
            sample_times = []
            for line in sample_result.stdout.split('\n'):
                if 'Sample Time' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        time_str = parts[1].strip()
                        try:
                            # Пробуем преобразовать в секунды
                            t = datetime.strptime(time_str, '%H:%M:%S')
                            seconds = t.hour * 3600 + t.minute * 60 + t.second
                            sample_times.append(seconds)
                        except:
                            pass

            if sample_times:
                print(f"✅ Найдено {len(sample_times)} временных меток")

        # 3. Создаем GPX файл
        gpx_path = os.path.splitext(video_path)[0] + '_extracted.gpx'

        print(f"💾 Создание GPX файла: {gpx_path}")

        # Создаем структуру GPX
        gpx = ET.Element('gpx', {
            'version': '1.1',
            'creator': 'Video GPS Extractor',
            'xmlns': 'http://www.topografix.com/GPX/1/1'
        })

        # Добавляем метаданные
        metadata_elem = ET.SubElement(gpx, 'metadata')
        time_elem = ET.SubElement(metadata_elem, 'time')
        time_elem.text = datetime.now().isoformat()

        # Создаем трек
        trk = ET.SubElement(gpx, 'trk')
        name = ET.SubElement(trk, 'name')
        name.text = f"GPS Track from {os.path.basename(video_path)}"

        trkseg = ET.SubElement(trk, 'trkseg')

        # Добавляем точки трека
        # Для простоты, если есть SampleTime, используем их,
        # иначе используем только одну точку (если есть)

        points_added = 0

        # Пробуем получить список всех GPS точек
        # Это сложная часть - в разных видео GPS данные хранятся по-разному

        # Вариант: Используем -ee (extract embedded) опцию для получения всех данных
        if True:  # Пробуем расширенный режим
            print("🔄 Попытка извлечь все встроенные GPS данные...")

            # Создаем временный файл для вывода
            all_cmd = ['exiftool', '-ee', '-gpslatitude', '-gpslongitude', '-gpsdatetime', '-j', video_path]
            all_result = subprocess.run(all_cmd, capture_output=True, text=True)

            try:
                all_data = json.loads(all_result.stdout)

                if len(all_data) > 1:  # Есть несколько записей
                    print(f"✅ Найдено {len(all_data)} записей с данными")

                    for i, entry in enumerate(all_data):
                        if 'GPSLatitude' in entry and 'GPSLongitude' in entry:
                            # Определяем время
                            timestamp = None
                            if 'GPSDateTime' in entry:
                                try:
                                    # Преобразуем "2024:11:06 17:58:31Z" в datetime
                                    dt_str = entry['GPSDateTime']
                                    dt_str = dt_str.replace(':', '-', 2)  # Заменяем первые два : на -
                                    timestamp = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                                except:
                                    timestamp = datetime.now() - timedelta(hours=i)
                            else:
                                # Если нет времени, используем приблизительное
                                timestamp = datetime.now() - timedelta(hours=len(all_data) - i)

                            # Добавляем точку
                            trkpt = ET.SubElement(trkseg, 'trkpt', {
                                'lat': str(entry['GPSLatitude']),
                                'lon': str(entry['GPSLongitude'])
                            })

                            if timestamp:
                                time_pt = ET.SubElement(trkpt, 'time')
                                time_pt.text = timestamp.isoformat()

                            points_added += 1

            except json.JSONDecodeError:
                print("⚠️ Не удалось распарсить расширенный вывод")

        # Если не удалось получить несколько точек, используем одну
        if points_added == 0 and 'GPSLatitude' in metadata and 'GPSLongitude' in metadata:
            print("⚠️ Добавляем одиночную точку (только первые координаты)")

            trkpt = ET.SubElement(trkseg, 'trkpt', {
                'lat': str(metadata['GPSLatitude']),
                'lon': str(metadata['GPSLongitude'])
            })

            if 'GPSDateTime' in metadata:
                time_pt = ET.SubElement(trkpt, 'time')
                time_pt.text = metadata['GPSDateTime'].replace(':', '-', 2)

            points_added = 1

        if points_added == 0:
            print("❌ Не удалось добавить ни одной точки GPX")
            return None

        # Сохраняем GPX файл
        tree = ET.ElementTree(gpx)
        tree.write(gpx_path, encoding='utf-8', xml_declaration=True)

        print(f"✅ Успешно создан GPX файл с {points_added} точками")
        print(f"📁 Путь: {gpx_path}")

        return gpx_path

    except Exception as e:
        print(f"❌ Ошибка при извлечении GPS: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_gps_metadata(video_path):
    """
    Вспомогательная функция для отладки - показывает все метаданные
    """
    cmd = ['exiftool', '-json', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        metadata = json.loads(result.stdout)[0]

        print("\n📋 Доступные метаданные:")
        gps_keys = [k for k in metadata.keys() if 'GPS' in k or 'gps' in k.lower()]

        if gps_keys:
            print("📍 GPS теги:")
            for key in gps_keys:
                print(f"  {key}: {metadata[key]}")
        else:
            print("❌ GPS теги не найдены")
            print("Все теги:", list(metadata.keys()))

        return metadata
    else:
        print(f"❌ Ошибка: {result.stderr}")
        return None


# Для тестирования
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        extract_gpx_from_video(video_path)
    else:
        print("Укажите путь к видео файлу")