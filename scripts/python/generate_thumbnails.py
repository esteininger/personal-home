#!/usr/bin/env python3
"""
Generate resized JPEG thumbnails for every gallery.json entry and upload them
to S3 under album/thumb/, then write a thumb_url field back onto each entry.

The grid view is 3 columns inside a 900px container (~284px per column), so a
long-edge cap of 800px comfortably covers retina displays while cutting the
~2.4MB originals down to roughly 60-120KB each.

Usage (from repo root):
  python scripts/python/generate_thumbnails.py [--max-dim 800] [--quality 78] [--workers 8]

Requires: pip install boto3 Pillow requests
"""

import argparse
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
import requests
from PIL import Image, ImageOps

S3_BUCKET = "ethan.dev"
S3_THUMB_PREFIX = "album/thumb/"
CF_DOMAIN = "diyjmz7hrjx3w.cloudfront.net"
AWS_REGION = "us-east-1"


def thumb_key(url: str) -> str:
    filename = url.rstrip("/").split("/")[-1]
    return S3_THUMB_PREFIX + filename


def make_thumbnail(image_bytes: bytes, max_dim: int, quality: int) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)  # bake in EXIF rotation before resizing
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


def process_entry(entry: dict, s3, max_dim: int, quality: int) -> tuple:
    url = entry.get("url")
    if not url:
        return entry, None, "no url"
    key = thumb_key(url)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        thumb_bytes = make_thumbnail(resp.content, max_dim, quality)
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=thumb_bytes,
            ContentType="image/jpeg",
            CacheControl="public, max-age=31536000, immutable",
        )
        thumb_url = f"https://{CF_DOMAIN}/{key}"
        return entry, thumb_url, None
    except Exception as e:  # noqa: BLE001
        return entry, None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Generate + upload gallery thumbnails")
    parser.add_argument("--max-dim", type=int, default=800)
    parser.add_argument("--quality", type=int, default=78)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true", help="Regenerate even if thumb_url already set")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    gallery_path = os.path.join(repo_root, "images", "gallery.json")
    with open(gallery_path, "r", encoding="utf-8") as f:
        gallery = json.load(f)

    todo = [e for e in gallery if args.force or not e.get("thumb_url")]
    print(f"{len(gallery)} total entries, {len(todo)} need thumbnails")
    if not todo:
        print("Nothing to do.")
        return

    s3 = boto3.client("s3", region_name=AWS_REGION)

    done = 0
    failed = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_entry, e, s3, args.max_dim, args.quality): e for e in todo}
        for fut in as_completed(futures):
            entry, thumb_url, err = fut.result()
            if thumb_url:
                entry["thumb_url"] = thumb_url
                done += 1
            else:
                failed.append((entry.get("url"), err))
            if (done + len(failed)) % 25 == 0:
                print(f"  {done + len(failed)}/{len(todo)} processed ({done} ok, {len(failed)} failed)")

    with open(gallery_path, "w", encoding="utf-8") as f:
        json.dump(gallery, f, indent=2)
        f.write("\n")

    print(f"\nDone: {done} thumbnails uploaded, {len(failed)} failed")
    for url, err in failed:
        print(f"  FAILED {url}: {err}")
    print(f"Wrote {gallery_path}")


if __name__ == "__main__":
    main()
