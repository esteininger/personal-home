#!/usr/bin/env python3
import argparse, sys, json, logging
from PIL import Image, ExifTags

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

def _to_float(x):
    try:
        return float(x.numerator) / float(x.denominator)
    except AttributeError:
        if isinstance(x, tuple) and len(x) == 2:
            return float(x[0]) / float(x[1])
        return float(x)

def dms_to_dd(dms):
    d, m, s = (_to_float(dms[0]), _to_float(dms[1]), _to_float(dms[2]))
    return d + (m / 60.0) + (s / 3600.0)

def extract_lat_lng(path):
    img = Image.open(path)
    exif = img._getexif()
    if not exif:
        return None

    exif_data = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
    gps = exif_data.get("GPSInfo")
    if not gps:
        return None

    gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
    lat, lat_ref = gps_tags.get("GPSLatitude"), gps_tags.get("GPSLatitudeRef", "N")
    lng, lng_ref = gps_tags.get("GPSLongitude"), gps_tags.get("GPSLongitudeRef", "E")

    if not (lat and lng):
        return None

    lat_dd = dms_to_dd(lat)
    lng_dd = dms_to_dd(lng)
    if str(lat_ref).upper() == "S":
        lat_dd = -lat_dd
    if str(lng_ref).upper() == "W":
        lng_dd = -lng_dd

    return {"lat": round(lat_dd, 6), "lng": round(lng_dd, 6)}

def main():
    parser = argparse.ArgumentParser(description="Extract lat/lng from image EXIF")
    parser.add_argument("paths", nargs="+", help="Image file(s)")
    args = parser.parse_args()

    for path in args.paths:
        result = extract_lat_lng(path)
        if result:
            logging.info(f"{path}: lat={result['lat']}, lng={result['lng']}")
            # still emit JSON if you want to pipe output
            print(json.dumps({"file": path, **result}))
        else:
            logging.warning(f"{path}: No EXIF GPS data found")

if __name__ == "__main__":
    main()
