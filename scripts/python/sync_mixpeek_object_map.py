#!/usr/bin/env python3
"""
Write images/mixpeek-objects.json: Mixpeek bucket object id -> gallery photo URL.

The album's search matches Mixpeek results back to gallery photos. Search results
carry the object id inside their thumbnail_url, but no photo metadata, so the page
looks the object id up in this map.

Usage:
    MIXPEEK_API_KEY=... python scripts/python/sync_mixpeek_object_map.py

Rerun after uploading new photos to the bucket.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://api.mixpeek.com/v1"
NAMESPACE = "ns_ff4ce153f3"
BUCKET_ID = "bkt_beccab14"
ROOT = Path(__file__).resolve().parents[2]
GALLERY = ROOT / "images" / "gallery.json"
OUT = ROOT / "images" / "mixpeek-objects.json"


def list_objects(key):
    objects, cursor = [], None
    while True:
        url = f"{BASE_URL}/buckets/{BUCKET_ID}/objects/list?limit=500"
        if cursor:
            url += f"&cursor={cursor}"
        req = urllib.request.Request(url, data=b"{}", method="POST", headers={
            "Authorization": f"Bearer {key}",
            "X-Namespace": NAMESPACE,
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=60) as r:
            page = json.load(r)
        objects += page.get("results", [])
        cursor = (page.get("pagination") or {}).get("next_cursor")
        if not cursor:
            return objects


def main():
    key = os.environ.get("MIXPEEK_API_KEY")
    if not key:
        sys.exit("set MIXPEEK_API_KEY")
    gallery_urls = {p["url"] for p in json.loads(GALLERY.read_text())}
    mapping = {}
    for obj in list_objects(key):
        for blob in obj.get("blobs") or []:
            url = (blob.get("properties") or {}).get("url")
            if url in gallery_urls:
                mapping[obj["object_id"]] = url
    OUT.write_text(json.dumps(mapping, indent=0, sort_keys=True) + "\n")
    print(f"{len(mapping)} objects mapped to {len(gallery_urls)} gallery photos -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
