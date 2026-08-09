#!/usr/bin/env python3
"""
Fetch cluster data from Mixpeek and enrich gallery.json with cluster labels/colors.

Usage:
    python scripts/python/sync_mixpeek_clusters.py

Reads images/gallery.json, queries Mixpeek for cluster assignments,
and writes back enriched gallery.json with cluster_id, cluster_label, and cluster_color.
"""

import json
import os
import sys
import requests

API_KEY = os.environ.get(
    "MIXPEEK_API_KEY",
    "mxp_sk_qqmnf1vPmGpyCqLDg2x_47IgVeDdyDhwQkncN3PhqRkR1VOR8MSuJKXYcWwd7T4sdWU",
)
NAMESPACE = "ns_ff4ce153f3"
COLLECTION_ID = "col_961b58b0a5"
CLUSTER_ID = "clust_4255b2e3e4"
BASE_URL = "https://api.mixpeek.com/v1"

GALLERY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "images", "gallery.json")

CLUSTER_COLORS = [
    "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
    "#ec4899", "#06b6d4", "#f97316", "#14b8a6", "#a855f7",
    "#6366f1", "#84cc16", "#e11d48", "#0ea5e9", "#d946ef",
]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "X-Namespace": NAMESPACE,
    "Content-Type": "application/json",
}


def fetch_all_documents():
    """Fetch all documents from the collection with pagination."""
    docs = []
    cursor = None
    while True:
        params = {"page_size": 100}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(
            f"{BASE_URL}/documents",
            headers=headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            break
        docs.extend(results)
        cursor = data.get("pagination", {}).get("next_cursor")
        if not cursor:
            break
    return docs


def fetch_cluster_results():
    """Fetch cluster execution results."""
    resp = requests.get(
        f"{BASE_URL}/clusters/{CLUSTER_ID}",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def build_cluster_map(documents):
    """Build a mapping from CloudFront URL to cluster info."""
    url_to_cluster = {}
    for doc in documents:
        payload = doc.get("payload", {})
        filename = payload.get("filename", "")
        cluster_info = payload.get("cluster", {})
        cluster_id = cluster_info.get("cluster_id")
        cluster_label = cluster_info.get("label", "")

        if not filename:
            continue

        cdn_url = f"https://diyjmz7hrjx3w.cloudfront.net/album/{filename}"
        url_to_cluster[cdn_url] = {
            "cluster_id": cluster_id,
            "cluster_label": cluster_label,
        }
    return url_to_cluster


def enrich_gallery(gallery, url_to_cluster, cluster_labels):
    """Add cluster data to each gallery entry."""
    color_map = {}
    color_idx = 0

    for entry in gallery:
        url = entry.get("url", "")
        info = url_to_cluster.get(url, {})
        cid = info.get("cluster_id")

        if cid is not None:
            if cid not in color_map:
                color_map[cid] = CLUSTER_COLORS[color_idx % len(CLUSTER_COLORS)]
                color_idx += 1
            entry["cluster_id"] = cid
            entry["cluster_label"] = info.get("cluster_label", cluster_labels.get(cid, f"Cluster {cid}"))
            entry["cluster_color"] = color_map[cid]
        else:
            entry["cluster_id"] = None
            entry["cluster_label"] = "Unclustered"
            entry["cluster_color"] = "#9ca3af"

    return gallery


def main():
    gallery_path = os.path.abspath(GALLERY_PATH)
    with open(gallery_path) as f:
        gallery = json.load(f)
    print(f"Loaded {len(gallery)} photos from gallery.json")

    print("Fetching documents from Mixpeek...")
    documents = fetch_all_documents()
    print(f"  Got {len(documents)} documents")

    if not documents:
        print("No documents found — batch processing may still be running.")
        print("Check status: curl -s -H 'Authorization: Bearer $MIXPEEK_API_KEY' "
              f"-H 'X-Namespace: {NAMESPACE}' "
              f"'{BASE_URL}/tasks/<task_id>'")
        sys.exit(1)

    print("Fetching cluster info...")
    try:
        cluster_data = fetch_cluster_results()
        cluster_labels = {}
        for group in cluster_data.get("cluster_groups", []):
            cid = group.get("cluster_id")
            label = group.get("label", "")
            if cid is not None:
                cluster_labels[cid] = label
        print(f"  Found {len(cluster_labels)} cluster labels")
    except Exception as e:
        print(f"  Warning: could not fetch cluster labels: {e}")
        cluster_labels = {}

    url_to_cluster = build_cluster_map(documents)
    matched = sum(1 for p in gallery if p.get("url") in url_to_cluster)
    print(f"  Matched {matched}/{len(gallery)} photos to Mixpeek documents")

    gallery = enrich_gallery(gallery, url_to_cluster, cluster_labels)

    with open(gallery_path, "w") as f:
        json.dump(gallery, f, indent=2)
        f.write("\n")
    print(f"Wrote enriched gallery.json ({len(gallery)} entries)")

    clusters_used = set(e.get("cluster_id") for e in gallery if e.get("cluster_id") is not None)
    print(f"\nClusters found: {len(clusters_used)}")
    for cid in sorted(clusters_used):
        label = next((e["cluster_label"] for e in gallery if e.get("cluster_id") == cid), "?")
        count = sum(1 for e in gallery if e.get("cluster_id") == cid)
        print(f"  [{cid}] {label} ({count} photos)")


if __name__ == "__main__":
    main()
