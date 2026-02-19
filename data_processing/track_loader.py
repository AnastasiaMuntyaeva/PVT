import xml.etree.ElementTree as ET
from datetime import datetime

def load_gpx(path):
    tree = ET.parse(path)
    root = tree.getroot()

    ns = {"gpx": "http://www.topografix.com/GPX/1/1"}

    points = []

    for trkpt in root.findall(".//gpx:trkpt", ns):
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])

        t = datetime.fromisoformat(
            trkpt.find("gpx:time", ns).text.replace("Z", "+00:00")
        )

        points.append({
            "lat": lat,
            "lon": lon,
            "time": t
        })

    # --- НОРМАЛИЗАЦИЯ ВРЕМЕНИ ---
    if points:
        t0 = points[0]["time"]
        for p in points:
            p["sec"] = (p["time"] - t0).total_seconds()

    return points