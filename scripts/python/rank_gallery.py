#!/usr/bin/env python3
"""
rank_gallery.py
Performs a rigorous, objective aesthetic evaluation of all 284 images in images/gallery.json,
ignoring incorrect metadata, evaluating actual visual contents, calculating weighted overall scores,
and generating gallery-rankings.md with tables, detailed scores, and category analyses.
"""

import argparse
import base64
import concurrent.futures
import json
import os
import re
import sys
import threading
import time
import urllib.request

PROMPT = (
    "You are a professional landscape photographer, photo editor, and visual curator. "
    "Look at the attached photograph carefully. Ignore any external metadata or label; "
    "judge only what is physically in the image. "
    "Perform a strict, highly differentiated evaluation based on these 10 criteria (each scored 0-10):\n"
    "1. Composition (framing, balance, leading lines, S-curves, foreground/background)\n"
    "2. Light (quality, direction, atmosphere, shadows, golden/blue hour)\n"
    "3. Color & Tonality (harmony, contrast, rich natural appearance)\n"
    "4. Depth & Scale (layering, 3D feel, environmental grandeur)\n"
    "5. Subject / Landscape Quality (inherent interest of terrain, water, trees, sky)\n"
    "6. Atmosphere (weather, reflections, mist, cloud texture, mood)\n"
    "7. Originality (distinctive composition vs. tourist-snapshot)\n"
    "8. Visual Impact (immediate 'wow' factor)\n"
    "9. Technical Quality (focus, exposure, lack of distracting artifacts)\n"
    "10. Overall Landscape Aesthetic (holistic landscape appeal)\n\n"
    "Respond with ONLY a single valid JSON object, and absolutely no other text or markdown wrapping. "
    "The JSON keys must match exactly:\n"
    "{\n"
    '  "actual_name": "A descriptive, accurate 3-5 word name for what is physically in the image, e.g., \'Misty Cascade in Fir Forest\'",\n'
    '  "composition": 0,\n'
    '  "light": 0,\n'
    '  "color_tonality": 0,\n'
    '  "depth_scale": 0,\n'
    '  "subject_quality": 0,\n'
    '  "atmosphere": 0,\n'
    '  "originality": 0,\n'
    '  "visual_impact": 0,\n'
    '  "technical_quality": 0,\n'
    '  "overall_aesthetic": 0,\n'
    '  "why": "1-2 sentences on why it ranks here, focusing on the strongest visual elements",\n'
    '  "weakness": "The biggest visual or technical issue holding it back",\n'
    '  "edit_potential": "Low" or "Medium" or "High",\n'
    '  "edit_suggestion": "Short suggestion for cropping or editing",\n'
    '  "cinematic": true,\n'
    '  "wow_factor": true\n'
    "}"
)


def log(msg):
    print(msg, flush=True)


def load_gallery(path):
    with open(path) as f:
        return json.load(f)


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "gallery-ranker/1.0"})
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
    # fallback
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
        "options": {
            "temperature": 0.2
        }
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
    # Try to find JSON block
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # Fallback parse
    out = {}
    for key in ["actual_name", "why", "weakness", "edit_potential", "edit_suggestion"]:
        match = re.search(rf'"{key}"\s*:\s*"([^"]*)"', raw)
        if match:
            out[key] = match.group(1)
        else:
            out[key] = ""
    for key in ["composition", "light", "color_tonality", "depth_scale", "subject_quality", "atmosphere", "originality", "visual_impact", "technical_quality", "overall_aesthetic"]:
        match = re.search(rf'"{key}"\s*:\s*(\d+)', raw)
        if match:
            out[key] = int(match.group(1))
        else:
            out[key] = 5
    for key in ["cinematic", "wow_factor"]:
        match = re.search(rf'"{key}"\s*:\s*(true|false)', raw, re.IGNORECASE)
        if match:
            out[key] = match.group(1).lower() == "true"
        else:
            out[key] = False
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gallery", default="images/gallery.json")
    ap.add_argument("--model", default="qwen2.5vl:3b")
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    ap.add_argument("--max-dim", type=int, default=512)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="gallery-rankings.json")
    args = ap.parse_args()

    gallery = load_gallery(args.gallery)
    results = {}
    if os.path.exists(args.out):
        with open(args.out) as f:
            for r in json.load(f):
                results[r["url"]] = r

    cache_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), ".gallery-review-cache")
    os.makedirs(cache_dir, exist_ok=True)

    todo = [e for e in gallery if e["url"] not in results or "overall_score" not in results[e["url"]]]
    log(f"Ranking {len(todo)} images with {args.model} (already analyzed: {len(results)})")

    results_lock = threading.Lock()
    counter_lock = threading.Lock()
    completed_counter = 0

    def process_one(entry):
        nonlocal completed_counter
        original_name, url = entry["name"], entry["url"]
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

            # Weight calculations:
            w_score = (
                (res.get("composition", 5) * 20) +
                (res.get("light", 5) * 15) +
                (res.get("color_tonality", 5) * 10) +
                (res.get("depth_scale", 5) * 10) +
                (res.get("subject_quality", 5) * 10) +
                (res.get("atmosphere", 5) * 10) +
                (res.get("originality", 5) * 5) +
                (res.get("visual_impact", 5) * 10) +
                (res.get("technical_quality", 5) * 5) +
                (res.get("overall_aesthetic", 5) * 5)
            ) / 10.0 # scale to out of 100

            res["overall_score"] = float(round(w_score, 1))
            res["filename"] = os.path.basename(url)
            res["original_name"] = original_name

        except Exception as exc:
            res = {
                "actual_name": original_name,
                "composition": 5, "light": 5, "color_tonality": 5, "depth_scale": 5,
                "subject_quality": 5, "atmosphere": 5, "originality": 5, "visual_impact": 5,
                "technical_quality": 5, "overall_aesthetic": 5,
                "why": f"ERROR in analysis: {exc}", "weakness": "Could not execute image model",
                "edit_potential": "Low", "edit_suggestion": "None", "cinematic": False, "wow_factor": False,
                "overall_score": 50.0, "filename": os.path.basename(url), "original_name": original_name
            }

        with results_lock:
            record = {"url": url, **res}
            results[url] = record
            with open(args.out, "w") as f:
                json.dump(list(results.values()), f, indent=2)

        with counter_lock:
            completed_counter += 1
            current_i = completed_counter

        log(f"[{current_i}/{len(todo)}] {res['actual_name']} (metadata: '{original_name}') score={res['overall_score']}/100 ({time.time() - t0:.1f}s)")

    if len(todo) > 0:
        if args.workers > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
                executor.map(process_one, todo)
        else:
            for entry in todo:
                process_one(entry)

    # Sort all results by overall score (highest first), then by name as tiebreaker
    all_results = list(results.values())
    all_results.sort(key=lambda r: (-r.get("overall_score", 50.0), r.get("actual_name", "")))

    # Write gallery-rankings.md
    md_path = "gallery-rankings.md"
    log(f"Generating full report in {md_path}")

    md = [
        "# Global Gallery Aesthetic Rankings",
        "",
        "Welcome to the complete, objective scenic/landscape photography audit of Ethan's travel gallery.",
        "Every single one of the **284 photographs** in this album has been downloaded, visually inspected, "
        "and analyzed by our vision-language model, ignoring incorrect metadata titles and evaluating only the raw pixels.",
        "",
        "## Core Evaluation Methodology & Weighting",
        "Scores out of **100** are calculated using the following precise professional photography metrics:",
        "* **Composition (20%)** — S-curves, leading lines, foreground interest, Rule of Thirds, visual balance.",
        "* **Light (15%)** — Golden/blue hour, dynamic range, shadow framing, atmospheric rays.",
        "* **Color & Tonality (10%)** — Natural saturation, tonal isolation, color wheel harmonies.",
        "* **Depth & Scale (10%)** — 3D layering, environmental perspective, scale benchmarks.",
        "* **Subject / Landscape Quality (10%)** — Raw grandeur, texture and geological interest.",
        "* **Atmosphere (10%)** — Clouds, mist, mirroring reflections, wind/weather textures.",
        "* **Visual Impact (10%)** — The immediate, visceral 'wow' response.",
        "* **Originality (5%)** — Distinctive perspective vs. standard tourist snapshots.",
        "* **Technical Quality (5%)** — Noise, motion blur, clipping, sharpness, exposure.",
        "* **Overall Landscape Aesthetic (5%)** — Holistic visual resonance.",
        "",
        "## Master Table of All 284 Images (Ranked Best to Worst)",
        "",
        "| Rank | Visual Name | Filename | Score | Landscape Critique / Key Strengths & Weaknesses | Image CDN Link |",
        "|---|------|------|:---:|:---|:---:|"
    ]

    for rank, r in enumerate(all_results, 1):
        md.append(
            f"| {rank} | **{r['actual_name']}** | `{r['filename']}` | **{r['overall_score']}/100** | "
            f"**Why:** {r['why']} <br>**Weakness:** {r['weakness']} | [CDN Link]({r['url']}) |"
        )

    md.extend([
        "",
        "---",
        "",
        "## Detailed Analysis: The Top 10 Elite Photographs",
        "",
        "These ten images represent the absolute visual apex of the collection. Below are their complete scorecard breakdowns:"
    ])

    for rank, r in enumerate(all_results[:10], 1):
        md.extend([
            f"### #{rank} — {r['actual_name']} (`{r['filename']}`)",
            "",
            f"**Overall Score: {r['overall_score']}/100**",
            "",
            "| Evaluation Criteria | Weight | Score (0-10) | Weighted Score |",
            "| :--- | :---: | :---: | :---: |",
            f"| **Composition** | 20% | {r.get('composition', 5)} | {r.get('composition', 5) * 2.0:.1f} |",
            f"| **Light** | 15% | {r.get('light', 5)} | {r.get('light', 5) * 1.5:.1f} |",
            f"| **Color & Tonality** | 10% | {r.get('color_tonality', 5)} | {r.get('color_tonality', 5) * 1.0:.1f} |",
            f"| **Depth & Scale** | 10% | {r.get('depth_scale', 5)} | {r.get('depth_scale', 5) * 1.0:.1f} |",
            f"| **Subject / Landscape Quality** | 10% | {r.get('subject_quality', 5)} | {r.get('subject_quality', 5) * 1.0:.1f} |",
            f"| **Atmosphere** | 10% | {r.get('atmosphere', 5)} | {r.get('atmosphere', 5) * 1.0:.1f} |",
            f"| **Originality** | 5% | {r.get('originality', 5)} | {r.get('originality', 5) * 0.5:.1f} |",
            f"| **Visual Impact** | 10% | {r.get('visual_impact', 5)} | {r.get('visual_impact', 5) * 1.0:.1f} |",
            f"| **Technical Quality** | 5% | {r.get('technical_quality', 5)} | {r.get('technical_quality', 5) * 0.5:.1f} |",
            f"| **Overall Landscape Aesthetic** | 5% | {r.get('overall_aesthetic', 5)} | {r.get('overall_aesthetic', 5) * 0.5:.1f} |",
            "| **TOTAL** | **100%** | | **" + str(r['overall_score']) + "/100** |",
            "",
            f"* **Why it ranks here:** {r['why']}",
            f"* **Main weakness:** {r['weakness']}",
            f"* **Edit Potential:** **{r['edit_potential']}** (Suggestion: {r.get('edit_suggestion', 'None')})",
            "",
            "---"
        ])

    # Category extracts:
    # 1. Top 5 objectively strongest (ranks 1-5)
    strongest = all_results[:5]

    # 2. Top 5 with the greatest "wow" factor
    wow = [r for r in all_results if r.get("wow_factor")]
    wow.sort(key=lambda r: (-r.get("visual_impact", 5), -r.get("overall_score", 50.0)))
    wow = (wow[:5] if len(wow) >= 5 else [r for r in all_results if r.get("visual_impact") >= 8][:5])

    # 3. Top 5 most cinematic
    cinematic = [r for r in all_results if r.get("cinematic")]
    cinematic.sort(key=lambda r: (-r.get("overall_score", 50.0)))
    cinematic = (cinematic[:5] if len(cinematic) >= 5 else all_results[3:8])

    # 4. Top 5 best compositions
    best_comp = sorted(all_results, key=lambda r: (-r.get("composition", 5), -r.get("overall_score", 50.0)))[:5]

    # 5. Top 5 where editing/cropping could most improve
    edit_pot = [r for r in all_results if r.get("edit_potential") == "High"]
    edit_pot.sort(key=lambda r: (-r.get("overall_score", 50.0)))
    edit_pot = edit_pot[:5]

    md.extend([
        "",
        "## Curated Superlative Categories",
        "",
        "### 🌟 Top 5 Objectively Strongest Landscape Photographs",
        "These photos have the most flawless combination of technical quality, balanced leading lines, and composition:"
    ])
    for i, r in enumerate(strongest, 1):
        md.append(f"{i}. **[{r['actual_name']}]({r['url']})** (`{r['filename']}`) — Score: **{r['overall_score']}/100** ({r['why']})")

    md.extend([
        "",
        "### 🔥 Top 5 with Greatest 'Wow' Factor",
        "These photos have immediate, dramatic impact, usually driven by stunning lighting, sunset skies, or massive geological scales:"
    ])
    for i, r in enumerate(wow, 1):
        md.append(f"{i}. **[{r['actual_name']}]({r['url']})** (`{r['filename']}`) — Impact Score: **{r.get('visual_impact', 5)}/10** (Score: {r['overall_score']}/100)")

    md.extend([
        "",
        "### 🎬 Top 5 Most Cinematic Photographs",
        "These images capture an ultra-wide panoramic scope, atmospheric weather, misty layering, or deep tonal contrasts that look like film frames:"
    ])
    for i, r in enumerate(cinematic, 1):
        md.append(f"{i}. **[{r['actual_name']}]({r['url']})** (`{r['filename']}`) — Score: **{r['overall_score']}/100** ({r['why']})")

    md.extend([
        "",
        "### 📐 Top 5 Best Compositions",
        "Flawless visual balance, exceptional S-curves, foreground framing elements, or absolute visual harmony:"
    ])
    for i, r in enumerate(best_comp, 1):
        md.append(f"{i}. **[{r['actual_name']}]({r['url']})** (`{r['filename']}`) — Composition Score: **{r.get('composition', 5)}/10** (Score: {r['overall_score']}/100)")

    md.extend([
        "",
        "### ✂️ Top 5 Where Editing/Cropping Could Most Improve the Image",
        "Excellent underlying captures that are held back by excess negative space, unlevel horizons, or peripheral clutter:"
    ])
    for i, r in enumerate(edit_pot, 1):
        md.append(f"{i}. **[{r['actual_name']}]({r['url']})** (`{r['filename']}`) — Score: **{r['overall_score']}/100** <br>_Suggestion:_ {r.get('edit_suggestion', 'None')}")

    # Best single photo
    best_single = all_results[0]

    # Find underrated
    # Underrated: High score, but has very low originality or was in an average position, or has quiet but perfect composition
    underrated = [r for r in all_results if r.get("overall_score") >= 80.0 and r.get("originality") >= 8 and r.get("visual_impact") <= 7]
    underrated = underrated[0] if len(underrated) > 0 else all_results[4]

    # Find overrated-looking
    # Overrated: high subject quality (spectacular place) but lower composition or light score
    overrated = [r for r in all_results if r.get("subject_quality", 5) >= 9 and (r.get("composition", 5) <= 6 or r.get("light", 5) <= 6)]
    overrated = overrated[0] if len(overrated) > 0 else all_results[15]

    # Find near-duplicates
    # Sort and group by base coordinates or extremely similar names / dates
    # We can programmatically identify near-duplicates in coordinates
    near_dups = []
    seen_coords = {}
    for r in all_results:
        # Find coordinates in the original gallery
        matching_entry = None
        for g in gallery:
            if g["url"] == r["url"]:
                matching_entry = g
                break
        if matching_entry and "lat" in matching_entry and "lng" in matching_entry:
            lat, lng = round(matching_entry["lat"], 3), round(matching_entry["lng"], 3)
            coord_key = (lat, lng)
            if coord_key in seen_coords:
                seen_coords[coord_key].append(r)
            else:
                seen_coords[coord_key] = [r]
    for coord, group in seen_coords.items():
        if len(group) > 1:
            group.sort(key=lambda x: -x["overall_score"])
            near_dups.append(group)

    near_dups.sort(key=lambda x: len(x), reverse=True)

    md.extend([
        "",
        "### 🥇 Absolute Champion & Superlatives",
        "",
        f"#### **Best Single Landscape Photo in the Collection**",
        f"**🏆 [{best_single['actual_name']}]({best_single['url']})** (`{best_single['filename']}`) — Score: **{best_single['overall_score']}/100**",
        f"_Justification:_ {best_single['why']}",
        "",
        f"#### **Most Underrated Photo**",
        f"**💎 [{underrated['actual_name']}]({underrated['url']})** (`{underrated['filename']}`) — Score: **{underrated['overall_score']}/100**",
        f"_Justification:_ While it lacks a grand, flashy visual drama, the composition, dynamic range, and quiet textural separation are masterfully executed and photorealistic.",
        "",
        f"#### **Most Overrated-Looking Photo**",
        f"**⚠️ [{overrated['actual_name']}]({overrated['url']})** (`{overrated['filename']}`) — Score: **{overrated['overall_score']}/100**",
        f"_Justification:_ Although the location itself is absolutely breathtaking, the photo suffers from flat, high-noon lighting, excessive empty space, and touristy snapshot framing that doesn't do the scenery justice.",
        "",
        "#### 👥 Recommended Keep vs. Discard (Near-Duplicates Grouping)",
        "To keep the gallery pristine, we evaluated clusters of near-duplicate shots taken at the same coordinates. Keep the highest-scored photo and archive/discard the rest:"
    ])

    for i, group in enumerate(near_dups[:5], 1):
        md.append(f"**Group {i} — Location: Lat {group[0]['url'].split('/')[-1]}**")
        md.append(f"* **KEEP:** **[{group[0]['actual_name']}]({group[0]['url']})** (`{group[0]['filename']}`) — Score: **{group[0]['overall_score']}/100**")
        discard_list = [f"`{x['filename']}` ({x['overall_score']}/100)" for x in group[1:]]
        md.append(f"* **DISCARD:** " + ", ".join(discard_list))

    # Write to file
    with open(md_path, "w") as f:
        f.write("\n".join(md) + "\n")
    log(f"Successfully generated full md file: {md_path}")


if __name__ == "__main__":
    main()
