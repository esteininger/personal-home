#!/usr/bin/env python3
"""
Bulk add images in a directory using the existing add_to_gallery.py logic.

Defaults:
  - Input directory: <repo_root>/album_inbox
  - Uses the same S3 bucket/prefix/CloudFront/region as add_to_gallery.py
  - Derives a default "name" from the filename (stem), unless --name-empty is passed
  - Moves processed files to <input_dir>/processed when successful (configurable)

Usage examples:
  python scripts/python/bulk_add_to_gallery.py
  python scripts/python/bulk_add_to_gallery.py --dir /abs/path/to/folder
  python scripts/python/bulk_add_to_gallery.py --name-empty --no-move
  python scripts/python/bulk_add_to_gallery.py --bucket ethan.dev --prefix album/
"""

import argparse
import os
import sys
import shutil
from typing import Iterable

# Import the single-file uploader to reuse its configuration and helpers
try:
    from . import add_to_gallery as single
except Exception:
    # Fallback for direct execution without package context
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    mod_path = os.path.join(here, 'add_to_gallery.py')
    spec = importlib.util.spec_from_file_location('add_to_gallery', mod_path)
    single = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(single)  # type: ignore


IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG', '.heic', '.HEIC'}


def iter_images(path: str) -> Iterable[str]:
    for root, _dirs, files in os.walk(path):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext in IMAGE_EXTS:
                yield os.path.join(root, fname)


def derive_name_from_filename(file_path: str) -> str:
    stem = os.path.splitext(os.path.basename(file_path))[0]
    # Replace underscores/dashes with spaces, collapse doubles, title-case softly
    pretty = stem.replace('_', ' ').replace('-', ' ')
    return ' '.join(pretty.split())


def process_one(file_path: str, args, repo_root: str) -> bool:
    try:
        lat, lng = args.lat, args.lng
        if lat is None or lng is None:
            gps = single.extract_lat_lng(file_path)
            if gps:
                lat, lng = gps
            else:
                lat, lng = None, None

        prefix = args.prefix.strip('/')
        if prefix:
            prefix = prefix + '/'
        key = prefix + single.make_key(file_path)

        single.upload_to_s3(file_path, args.bucket, key, region=args.region)
        url = f"https://{args.cf_domain}/{key}"

        name = '' if args.name_empty else derive_name_from_filename(file_path)
        date_taken = None
        try:
            date_taken = single.extract_date_taken(file_path)
        except Exception:
            pass
        single.append_to_gallery(repo_root, url, name, lat, lng, date_taken)

        if args.move:
            dest_dir = os.path.join(args.dir, 'processed')
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(file_path, os.path.join(dest_dir, os.path.basename(file_path)))
        print(f"[ok] {file_path}")
        return True
    except Exception as e:
        print(f"[err] {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Bulk upload images in a directory to S3 and append to gallery.json')
    # Directory of images
    default_inbox = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'album_inbox'))
    parser.add_argument('--dir', default=default_inbox, help='Directory to scan for images (defaults to album_inbox)')
    # Optional overrides mirroring add_to_gallery.py
    parser.add_argument('--bucket', default=single.S3_BUCKET)
    parser.add_argument('--prefix', default=single.S3_PREFIX)
    parser.add_argument('--cf-domain', dest='cf_domain', default=single.CF_DOMAIN)
    parser.add_argument('--region', default=single.AWS_REGION)
    # Optional GPS override for all files
    parser.add_argument('--lat', type=float)
    parser.add_argument('--lng', type=float)
    # Behaviors
    parser.add_argument('--name-empty', action='store_true', help='Do not derive a name from filename; leave blank')
    parser.add_argument('--no-move', dest='move', action='store_false', help='Do not move processed files')
    parser.set_defaults(move=True)

    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        print(f"Input directory does not exist: {args.dir}", file=sys.stderr)
        sys.exit(1)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    files = list(iter_images(args.dir))
    if not files:
        print('No images found to process.')
        sys.exit(0)

    ok = 0
    for f in files:
        if process_one(f, args, repo_root):
            ok += 1

    print(f"\nCompleted. Success: {ok} / {len(files)}")


if __name__ == '__main__':
    main()


