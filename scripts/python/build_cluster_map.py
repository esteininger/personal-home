#!/usr/bin/env python3
"""
Pre-build images/clusters.json, the static file behind the Album > Clusters tab.

Usage:
    python scripts/python/build_cluster_map.py

The tab used to call Mixpeek live on every visit. This pulls the latest usable
cluster run once and writes only what the page draws: a cloud of dots, one point
per album photo, and a named card per cluster. Rerun it after a new cluster run.
"""

import collections
import json
import math
import random
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "images" / "clusters.json"
BASE_URL = "https://api.mixpeek.com/v1"
NAMESPACE = "ns_ff4ce153f3"
COLLECTION_ID = "col_961b58b0a5"

# The site's public read-only key, so it lives in one place.
API_KEY = re.search(r"MIXPEEK_KEY = '([^']+)'", (ROOT / "index.html").read_text()).group(1)
HEADERS = {"Authorization": f"Bearer {API_KEY}", "X-Namespace": NAMESPACE}

MAX_DUST = 7000
SCALE = 10000
PAD = 0.07
PLOT_ASPECT = 10 / 16  # height / width of the plot, keeps the clouds round
RING_X, RING_Y = 0.37, 0.33
MIN_DOTS, MAX_DOTS = 320, 2600

COLORS = {
    "large": "#4f9cf9",
    "rest": ["#a855f7", "#22d3c5", "#7c6cf7", "#fb923c", "#f87171", "#facc15", "#6ee05b", "#3b82f6", "#ec4899"],
}

# Mixpeek's generated labels on this run do not match the photos ("Sierra Nevada
# Alpine" is all Kauai), so name this run's clusters from what is in them. A new
# run falls back to Mixpeek's labels until it gets an entry here.
NAMES = {
    "clust_89f484fd0b": {
        "cl_0": "Pacific Coast",
        "cl_1": "Yosemite & Tahoe",
        "cl_2": "High Country",
        "cl_3": "Kauai",
        "cl_4": "North Cascades",
        "cl_5": "Central Oregon",
        "cl_6": "Mountain Lakes",
        "cl_7": "Big Peaks",
        "cl_8": "Mountain Streams",
        "cl_9": "Yellowstone",
    },
}


def get(path):
    resp = requests.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=120)
    resp.raise_for_status()
    return resp.json()


def pick_run():
    """Newest finished run with one centroid per cluster and real labels."""
    data = get(f"/clusters?collection_id={COLLECTION_ID}")
    runs = [c for c in (data if isinstance(data, list) else data["results"])
            if c["status"] == "COMPLETED" and COLLECTION_ID in (c.get("input_collections") or [])]
    runs.sort(key=lambda c: c.get("completed_at") or c.get("created_at"), reverse=True)
    for run in runs:
        points = get(f"/clusters/{run['cluster_id']}/visualization").get("points", [])
        centroids = [p for p in points if p.get("is_centroid")]
        members = [p for p in points if not p.get("is_centroid")]
        ids = [p["cluster_id"] for p in centroids]
        photos = sum(p.get("source_collection_id") == COLLECTION_ID for p in members)
        labeled = any(p.get("cluster_label") and not re.match(r"^Cluster \d+$", p["cluster_label"]) for p in centroids)
        if len(ids) >= 2 and len(set(ids)) == len(ids) and members and photos / len(members) > 0.9 and labeled:
            return run["cluster_id"], centroids, members
    raise SystemExit("no usable cluster run")


def document_objects():
    """document id -> source object id, across every page of the collection."""
    objects, cursor = {}, None
    while True:
        query = "page_size=500" + (f"&cursor={cursor}" if cursor else "")
        page = get(f"/collections/{COLLECTION_ID}/documents?{query}")
        docs = page.get("documents") or page.get("results") or []
        for doc in docs:
            lineage = (doc.get("_internal") or {}).get("lineage") or {}
            objects[doc["document_id"]] = lineage.get("source_object_id")
        cursor = (page.get("pagination") or {}).get("next_cursor")
        if not cursor or not docs:
            return objects


def main():
    random.seed(7)
    gallery = {g["url"]: g for g in json.loads((ROOT / "images" / "gallery.json").read_text())}
    object_urls = json.loads((ROOT / "images" / "mixpeek-objects.json").read_text())
    rankings = {r["url"]: r.get("overall_aesthetic", 0) for r in json.loads((ROOT / "gallery-rankings.json").read_text())}

    run_id, centroids, members = pick_run()
    objects = document_objects()

    xs, ys = [p["x"] for p in members], [p["y"] for p in members]
    x0, xr, y0, yr = min(xs), (max(xs) - min(xs)) or 1, min(ys), (max(ys) - min(ys)) or 1
    nx = lambda v: PAD + (1 - 2 * PAD) * (v - x0) / xr
    ny = lambda v: PAD + (1 - 2 * PAD) * (1 - (v - y0) / yr)

    by_photo = collections.defaultdict(list)
    for p in members:
        url = object_urls.get(objects.get(p["source_document_id"]))
        if url in gallery:
            by_photo[url].append(p)

    # A photo's cluster is where most of its copies landed.
    photo_cluster = {url: collections.Counter(p["cluster_id"] for p in points).most_common(1)[0][0]
                     for url, points in by_photo.items()}
    cluster_photos = collections.defaultdict(list)
    for url, cid in photo_cluster.items():
        cluster_photos[cid].append(url)

    ordered = sorted(cluster_photos, key=lambda c: -len(cluster_photos[c]))
    index = {cid: i for i, cid in enumerate(ordered)}
    labels = {p["cluster_id"]: p.get("cluster_label", "") for p in centroids}
    names = NAMES.get(run_id, {})
    members_of = collections.defaultdict(list)
    for p in members:
        if p["cluster_id"] in index:
            members_of[p["cluster_id"]].append((nx(p["x"]), ny(p["y"])))

    # The projected positions intermix, so membership would not read on screen.
    # Give each cluster its own cloud: the largest in the middle, the rest on a
    # ring in the order they sit around the projection's center.
    stats = {}
    for cid, pts in members_of.items():
        mx, my = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        sdx = (sum((p[0] - mx) ** 2 for p in pts) / len(pts)) ** 0.5 or 1
        sdy = (sum((p[1] - my) ** 2 for p in pts) / len(pts)) ** 0.5 or 1
        stats[cid] = (mx, my, sdx, sdy)
    centers = {ordered[0]: (0.5, 0.5)}
    ring = sorted(ordered[1:], key=lambda c: math.atan2(stats[c][1] - 0.5, stats[c][0] - 0.5))
    for i, cid in enumerate(ring):
        angle = -math.pi / 2 + 2 * math.pi * i / len(ring)
        centers[cid] = (0.5 + RING_X * math.cos(angle), 0.5 + RING_Y * math.sin(angle))
    largest = max(len(v) for v in members_of.values())
    sigma = {cid: 0.036 + 0.08 * math.sqrt(len(members_of[cid]) / largest) for cid in ordered}

    def place(x, y, cid, jitter=0.0):
        mx, my, sdx, sdy = stats[cid]
        zx, zy = (x - mx) / sdx, (y - my) / sdy
        reach = math.hypot(zx, zy)
        if reach > 2.4:
            zx, zy = zx * 2.4 / reach, zy * 2.4 / reach
        zx += random.gauss(0, jitter)
        zy += random.gauss(0, jitter)
        cx, cy = centers[cid]
        return (round(SCALE * max(0, min(1, cx + zx * sigma[cid] * PLOT_ASPECT))),
                round(SCALE * max(0, min(1, cy + zy * sigma[cid]))))

    photo_points = []
    for url, points in by_photo.items():
        x = sum(nx(p["x"]) for p in points) / len(points)
        y = sum(ny(p["y"]) for p in points) / len(points)
        cid = photo_cluster[url]
        photo_points.append((*place(x, y, cid, 0.2), index[cid], url))

    clusters = []
    for i, cid in enumerate(ordered):
        best = max(cluster_photos[cid], key=lambda u: rankings.get(u, 0))
        clusters.append({
            "name": names.get(cid) or labels.get(cid, "").split(" — ")[0],
            "count": len(cluster_photos[cid]),
            "color": COLORS["large"] if i == 0 else COLORS["rest"][(i - 1) % len(COLORS["rest"])],
            "x": round(SCALE * centers[cid][0]),
            "y": round(SCALE * centers[cid][1]),
            "thumb": gallery[best].get("thumb_url") or best,
        })

    dust = []
    total_members = sum(len(v) for v in members_of.values())
    for cid in ordered:
        pts = members_of[cid]
        wanted = max(MIN_DOTS, min(MAX_DOTS, round(MAX_DUST * len(pts) / total_members)))
        for x, y in random.choices(pts, k=wanted):
            dust += [*place(x, y, cid, 0.45), index[cid]]

    OUT.write_text(json.dumps({
        "run": run_id,
        "total": len(photo_points),
        "clusters": clusters,
        "dust": dust,
        "photos": [list(p) for p in photo_points],
    }, separators=(",", ":"), ensure_ascii=False))
    print(f"{OUT.name}: {OUT.stat().st_size // 1024} KB, {len(dust) // 3} dots, {len(photo_points)} photos, run {run_id}")
    for c in clusters:
        print(f"  {c['count']:>4}  {c['name']}")


if __name__ == "__main__":
    main()
