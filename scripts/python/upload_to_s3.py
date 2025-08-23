import boto3, sys, os, mimetypes

BUCKET = "ethan.dev"
PREFIX = "album/"

def upload(path, presign=False, expires=3600):
    s3 = boto3.client("s3")
    key = f"{PREFIX}{os.path.basename(path)}"

    content_type, _ = mimetypes.guess_type(path)
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    # Add cache control if you like:
    # extra["CacheControl"] = "public, max-age=31536000, immutable"

    try:
        s3.upload_file(path, BUCKET, key, ExtraArgs=extra)  # 🔑 no ACL here
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)

    print(f"✅ Uploaded to s3://{BUCKET}/{key}")

    # Plain S3 object URL (requires your bucket policy/CloudFront to allow reads)
    print(f"S3 URL: https://{BUCKET}.s3.amazonaws.com/{key}")

    if presign:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=expires,
        )
        print(f"Presigned (temporary) URL ({expires}s): {url}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_image.py <image_path> [--presign [seconds]]")
        sys.exit(1)

    path = sys.argv[1]
    presign = "--presign" in sys.argv
    try:
        exp_i = sys.argv.index("--presign")
        expires = int(sys.argv[exp_i + 1]) if exp_i + 1 < len(sys.argv) and sys.argv[exp_i + 1].isdigit() else 3600
    except ValueError:
        expires = 3600

    upload(path, presign=presign, expires=expires)
