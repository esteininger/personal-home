#!/usr/bin/env python3
"""
Review every image in images/gallery.json with a local vision model (ollama),
judging the actual photo, not the metadata, and produce an aesthetic ranking.

Usage (from repo root, outside the agent sandbox):
  python3 scripts/python/review_gallery.py                     # all 284, model qwen2.5vl
  python3 scripts/python/review_gallery.py --limit 10          # smoke test on first 10
  python3 scripts/python/review_gallery.py --model gemma3      # alternate vision model
  python3 scripts/python/review_gallery.py --start 100 --limit 50

Output (repo root):
  gallery-review.json    # per-image: name, url, description, strengths, weaknesses, score, raw
  gallery-review.md      # full ranking table, best first

The script resumes: images already scored in the output file are skipped.
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import time
import urllib.request

PROMPT = (
    "You are a strict but fair landscape photography critic. Look at the attached "
    "photograph carefully and judge the image itself. Respond with ONLY a single JSON "
    'object, no other text: {"description": "2-3 sentences: subject, composition, light, '
    'color", "strengths": "one short clause", "weaknesses": "one short clause or none", '
    '"score": N} where N is an integer 0-10. Rubric: 9-10 exceptional, museum-worthy '
    "composition and light; 7-8 strong, clearly publishable; 5-6 decent, one or two "
    "compelling elements; 3-4 weak, muddy, busy, or flat; 0-2 blurry, blown out, or "
    "unusable."
)


def log(msg):
    print(msg, flush=True)


def load_gallery(path):
    with open(path) as f:
        return json.load(f)


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "gallery-review/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        f.write(resp.read())
    return dest


def downscale(src_path, dest_path, max_dim):
    try:
        from PIL import Image

        with Image.open(src_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            scale = min(1.0, max_dim / max(w, h))
            if scale < 1.0:
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            img.save(dest_path, "JPEG", quality=85)
            return dest_path
    except ImportError:
        pass
    # macOS fallback
    import subprocess

    subprocess.run(["sips", "-Z", str(max_dim), "-s", "format", "jpeg", "-s", "formatOptions", "85",
                    src_path, "--out", dest_path], check=True, capture_output=True)
    return dest_path


def ask_model(base_url, model, image_b64, timeout=600):
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "user", "content": PROMPT, "images": [image_b64]}
        ],
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return data["message"]["content"]


def extract_result(raw):
    out = {"description": "", "strengths": "", "weaknesses": "", "score": None}
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            out["description"] = str(obj.get("description", ""))
            out["strengths"] = str(obj.get("strengths", ""))
            out["weaknesses"] = str(obj.get("weaknesses", ""))
            score = obj.get("score")
            if isinstance(score, (int, float)):
                out["score"] = int(score)
            elif isinstance(score, str):
                out["score"] = int(float(score))
        except (json.JSONDecodeError, ValueError):
            pass
    if out["score"] is None:
        m = re.search(r'("score"\s*:\s*)(\d{1,2})', raw)
        if m:
            out["score"] = int(m.group(2))
    if out["score"] is None:
        m = re.search(r"\b(\d{1,2})\s*/\s*10\b", raw)
        if m:
            out["score"] = int(m.group(1))
    out["raw"] = raw
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gallery", default="images/gallery.json")
    ap.add_argument("--model", default="qwen2.5vl")
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    ap.add_argument("--limit", type=int, default=0, help="review at most N images (0 = all)")
    ap.add_argument("--start", type=int, default=0, help="skip the first N images")
    ap.add_argument("--max-dim", type=int, default=2048, help="longest edge in pixels when downsizing")
    ap.add_argument("--out", default="gallery-review.json")
    args = ap.parse_args()

    gallery = load_gallery(args.gallery)
    results = {}
    if os.path.exists(args.out):
        with open(args.out) as f:
            for r in json.load(f):
                results[r["url"]] = r

    cache_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), ".gallery-review-cache")
    os.makedirs(cache_dir, exist_ok=True)

    todo = [e for e in gallery[args.start:] if e["url"] not in results or results[e["url"]].get("score") is None]
    if args.limit:
        todo = todo[: args.limit]

    log(f"Reviewing {len(todo)} images with '{args.model}' (already scored: {len(results)})")
    for i, entry in enumerate(todo, 1):
        name, url = entry["name"], entry["url"]
        t0 = time.time()
        try:
            raw_path = os.path.join(cache_dir, os.path.basename(url))
            download(url, raw_path)
            small_path = raw_path + ".small.jpg"
            downscale(raw_path, small_path, args.max_dim)
            with open(small_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            raw = ask_model(args.base_url, args.model, b64)
            res = extract_result(raw)
        except Exception as exc:
            log(f"[{i}/{len(todo)}] {name}  ERROR: {exc}")
            res = {"description": "", "strengths": "", "weaknesses": "", "score": None, "raw": f"ERROR: {exc}"}

        record = {"name": name, "url": url, **res}
        results[url] = record
        with open(args.out, "w") as f:
            json.dump(list(results.values()), f, indent=2)

        score = "n/a" if res["score"] is None else res["score"]
        log(f"[{i}/{len(todo)}] {name}  score={score}  ({time.time() - t0:.1f}s)")

    scored = [r for r in results.values() if r.get("score") is not None]
    scored.sort(key=lambda r: (-r["score"], r["name"]))
    log(f"\nDone. {len(scored)} scored, {len(results) - len(scored)} unscored.")

    md = ["# Gallery review (aesthetic ranking)", "",
          f"Model: {args.model}  -  {len(scored)} images scored  -  {time.strftime('%Y-%m-%d')}", "",
          "| # | Name | Score | Description | Strengths | Weaknesses |",
          "|---|------|-------|-------------|-----------|------------|"]
    for rank, r in enumerate(scored, 1):
        md.append(f"| {rank} | {r['name']} | {r['score']} | {r['description']} | {r['strengths']} | {r['weaknesses']} |")
    md_path = os.path.splitext(args.out)[0] + ".md"
    with open(md_path, "w") as f:
        f.write("\n".join(md) + "\n")
    log(f"Report written to {md_path}")

    top = scored[:10]
    log("\nTop 10 so far:")
    for rank, r in enumerate(top, 1):
        log(f"  {rank:2d}. [{r['score']}] {r['name']}")


if __name__ == "__main__":
    main()
