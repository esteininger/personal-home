#!/usr/bin/env python3
"""
Upload a local image to S3, extract GPS (EXIF), and append an entry to images/gallery.json.

Usage (from repo root):
  python scripts/albums/add_to_gallery.py --file /abs/path/to/IMG_1234.jpg \
      --bucket your-bucket --cf-domain dxxxx.cloudfront.net [--prefix album/] [--name "Place"] \
      [--lat 37.77 --lng -122.41] [--region us-east-1]

Requires: pip install boto3 Pillow
"""

import argparse
import json
import mimetypes
import os
import sys
import time
from typing import Optional, Tuple

import boto3
from PIL import Image, ExifTags


# =====================
# Hardcoded configuration
# =====================
# Change these to your values. Script will use these by default
S3_BUCKET   = "ethan.dev"
S3_PREFIX   = "album/"           # include trailing slash or leave empty
CF_DOMAIN   = "diyjmz7hrjx3w.cloudfront.net"
AWS_REGION  = "us-east-1"


def _to_float(x):
    try:
        return float(x.numerator) / float(x.denominator)
    except AttributeError:
        if isinstance(x, tuple) and len(x) == 2:
            return float(x[0]) / float(x[1])
        return float(x)


def _dms_to_dd(dms) -> float:
    d, m, s = (_to_float(dms[0]), _to_float(dms[1]), _to_float(dms[2]))
    return d + (m / 60.0) + (s / 3600.0)


def extract_lat_lng(path: str) -> Optional[Tuple[float, float]]:
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
    lat_dd = _dms_to_dd(lat)
    lng_dd = _dms_to_dd(lng)
    if str(lat_ref).upper() == "S":
        lat_dd = -lat_dd
    if str(lng_ref).upper() == "W":
        lng_dd = -lng_dd
    return round(lat_dd, 6), round(lng_dd, 6)


def detect_content_type(path_: str) -> str:
    ct, _ = mimetypes.guess_type(path_)
    return ct or "application/octet-stream"


def make_key(local_path: str) -> str:
    # Keep original file name (no suffix)
    return os.path.basename(local_path)


def upload_to_s3(file_path: str, bucket: str, key: str, region: Optional[str] = None):
    s3 = boto3.client("s3", region_name=region)
    extra = {"ContentType": detect_content_type(file_path)}
    s3.upload_file(file_path, bucket, key, ExtraArgs=extra)


def append_to_gallery(repo_root: str, url: str, name: str, lat: float, lng: float):
    gallery_path = os.path.join(repo_root, "images", "gallery.json")
    with open(gallery_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("images/gallery.json must contain a top-level array")
    data.append({"url": url, "name": name, "lat": lat, "lng": lng})
    with open(gallery_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Upload image → S3, extract GPS, append to gallery.json")
    parser.add_argument("--file", required=True, help="Absolute path to image file")
    parser.add_argument("--name", default="", help="Optional display name; blank if not provided")
    parser.add_argument("--lat", type=float, help="Override latitude if EXIF missing")
    parser.add_argument("--lng", type=float, help="Override longitude if EXIF missing")
    # Optional overrides, but defaults come from the hardcoded constants above
    parser.add_argument("--bucket", default=S3_BUCKET, help="S3 bucket (default from script)")
    parser.add_argument("--cf-domain", dest="cf_domain", default=CF_DOMAIN, help="CloudFront domain (default from script)")
    parser.add_argument("--prefix", default=S3_PREFIX, help="Key prefix (default from script)")
    parser.add_argument("--region", default=AWS_REGION, help="AWS region (default from script)")

    args = parser.parse_args()

    if not os.path.isabs(args.file):
        print("Please provide an absolute path to --file", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.file):
        print(f"File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    # Use hardcoded defaults (already in argparse), keep simple validation
    if not args.bucket:
        print("Missing S3 bucket", file=sys.stderr)
        sys.exit(1)
    if not args.cf_domain:
        print("Missing CloudFront domain", file=sys.stderr)
        sys.exit(1)

    lat, lng = args.lat, args.lng
    if lat is None or lng is None:
        gps = extract_lat_lng(args.file)
        if not gps:
            print("No EXIF GPS found and no --lat/--lng provided", file=sys.stderr)
            sys.exit(1)
        lat, lng = gps

    prefix = args.prefix.strip("/")
    if prefix:
        prefix = prefix + "/"
    key = prefix + make_key(args.file)

    upload_to_s3(args.file, args.bucket, key, region=args.region)
    url = f"https://{args.cf_domain}/{key}"

    # repo root = two levels up from this script
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    append_to_gallery(repo_root, url, args.name or "", lat, lng)

    print("\n✅ Done")
    print("URL:", url)
    print("Lat,Lng:", lat, ",", lng)
    print("Appended to:", os.path.join(repo_root, "images", "gallery.json"))


if __name__ == "__main__":
    main()


