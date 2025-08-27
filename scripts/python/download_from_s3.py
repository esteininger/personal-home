import os
import sys
import argparse
from typing import Iterable, List

import boto3


DEFAULT_BUCKET = "ethan.dev"
DEFAULT_PREFIX = "album/"


def is_probable_image_key(object_key: str) -> bool:
    """Return True if the S3 key looks like an image we care about.

    Uses file extension heuristics since list_objects_v2 doesn't include ContentType.
    """
    lowercase_key = object_key.lower()
    # Common still image formats; extend as needed
    valid_extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".heic",
        ".tiff",
        ".bmp",
    )
    return lowercase_key.endswith(valid_extensions) and not lowercase_key.endswith("/")


def ensure_directory(path: str) -> None:
    if not path:
        return
    os.makedirs(path, exist_ok=True)


def list_object_keys(bucket: str, prefix: str) -> Iterable[str]:
    """Yield all object keys in the bucket under the given prefix."""
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        contents = page.get("Contents", [])
        for item in contents:
            key = item.get("Key")
            if key:
                yield key


def download_objects(
    bucket: str,
    keys: Iterable[str],
    destination_dir: str,
    overwrite: bool = False,
) -> List[str]:
    """Download provided keys to destination_dir. Returns list of local file paths written."""
    s3 = boto3.client("s3")
    written: List[str] = []

    ensure_directory(destination_dir)

    for key in keys:
        # Only download filename portion; drop the prefix pathing
        filename = os.path.basename(key)
        if not filename:
            continue
        local_path = os.path.join(destination_dir, filename)

        if os.path.exists(local_path) and not overwrite:
            print(f"↩️  Skipping existing file: {local_path}")
            continue

        try:
            s3.download_file(bucket, key, local_path)
            print(f"✅ Downloaded s3://{bucket}/{key} -> {local_path}")
            written.append(local_path)
        except Exception as error:  # noqa: BLE001 - surface any boto issues
            print(f"❌ Failed to download s3://{bucket}/{key}: {error}")

    return written


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download all images from an S3 bucket prefix.",
    )
    parser.add_argument(
        "--bucket",
        default=DEFAULT_BUCKET,
        help=f"S3 bucket name (default: {DEFAULT_BUCKET})",
    )
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help=f"S3 prefix to scan (default: {DEFAULT_PREFIX})",
    )
    parser.add_argument(
        "--dest",
        default=os.path.join("scripts", "album_inbox"),
        help="Destination directory to save images (default: scripts/album_inbox)",
    )
    parser.add_argument(
        "--all-keys",
        action="store_true",
        help="Download all objects under prefix regardless of extension (not just images)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files if they already exist locally",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    keys = list_object_keys(args.bucket, args.prefix)
    if args.all_keys:
        keys_to_download = list(keys)
    else:
        keys_to_download = [k for k in keys if is_probable_image_key(k)]

    if not keys_to_download:
        print(
            f"No matching objects found under s3://{args.bucket}/{args.prefix}. "
            + ("Consider --all-keys to ignore extension filtering." if not args.all_keys else "")
        )
        return 0

    written = download_objects(
        bucket=args.bucket,
        keys=keys_to_download,
        destination_dir=args.dest,
        overwrite=bool(args.overwrite),
    )

    print(f"\nDone. Downloaded {len(written)} file(s) to {args.dest}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


