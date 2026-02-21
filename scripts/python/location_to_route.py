#!/usr/bin/env python3
"""
Convert a location history JSON file into a route for routes.json.

Usage:
  python location_to_route.py <location_history.json> [--route-id ID] [--update]

The location history JSON should be an array of objects with at least:
  { "lat": number, "lng": number, "timestamp": string }

This is the output format from the Location History Visualizer utility.

Options:
  --route-id ID   The route ID in routes.json to update (used with --update)
  --update        Update the matching route in routes.json with the new coordinates
  --simplify N    Keep every Nth point (default: auto based on total points)

Without --update, prints the coordinates array to stdout.
"""
import json
import sys
import math
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTES_JSON = REPO_ROOT / "routes.json"


def haversine_m(lat1, lon1, lat2, lon2):
    """Distance in meters between two lat/lng points."""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def simplify_route(points, min_distance_m=500, max_points=200):
    """
    Simplify a route by removing points that are too close together.
    Keeps first and last point always.
    """
    if len(points) <= 2:
        return points

    simplified = [points[0]]
    for pt in points[1:-1]:
        last = simplified[-1]
        dist = haversine_m(last[0], last[1], pt[0], pt[1])
        if dist >= min_distance_m:
            simplified.append(pt)
    simplified.append(points[-1])

    # If still too many points, subsample evenly
    if len(simplified) > max_points:
        step = len(simplified) / max_points
        resampled = []
        for i in range(max_points - 1):
            resampled.append(simplified[int(i * step)])
        resampled.append(simplified[-1])
        simplified = resampled

    return simplified


def load_location_history(path):
    """Load and parse a location history JSON file."""
    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Error: expected a JSON array", file=sys.stderr)
        sys.exit(1)

    # Extract lat/lng, sorted by timestamp
    points = []
    for entry in data:
        lat = entry.get("lat")
        lng = entry.get("lng")
        ts = entry.get("timestamp", "")
        if lat is not None and lng is not None:
            points.append((float(lat), float(lng), ts))

    # Sort by timestamp
    points.sort(key=lambda p: p[2])

    # Return [lat, lng, timestamp] triples
    return [[round(p[0], 6), round(p[1], 6), p[2]] for p in points]


def main():
    parser = argparse.ArgumentParser(description="Convert location history to route coordinates")
    parser.add_argument("input", help="Path to location history JSON file")
    parser.add_argument("--route-id", help="Route ID to update in routes.json")
    parser.add_argument("--update", action="store_true", help="Update routes.json in place")
    parser.add_argument("--min-distance", type=int, default=500,
                        help="Minimum distance in meters between points (default: 500)")
    parser.add_argument("--max-points", type=int, default=200,
                        help="Maximum number of points to keep (default: 200)")
    args = parser.parse_args()

    # Load and simplify
    raw_points = load_location_history(args.input)
    print(f"Loaded {len(raw_points)} raw points", file=sys.stderr)

    simplified = simplify_route(raw_points,
                                min_distance_m=args.min_distance,
                                max_points=args.max_points)
    print(f"Simplified to {len(simplified)} points", file=sys.stderr)

    if args.update and args.route_id:
        # Update routes.json
        if not ROUTES_JSON.exists():
            print(f"Error: {ROUTES_JSON} not found", file=sys.stderr)
            sys.exit(1)

        with open(ROUTES_JSON) as f:
            routes = json.load(f)

        found = False
        for route in routes:
            if route.get("id") == args.route_id:
                route["coordinates"] = simplified
                # Remove image if present — live map takes priority
                if "image" in route:
                    del route["image"]
                found = True
                break

        if not found:
            print(f"Error: route '{args.route_id}' not found in routes.json", file=sys.stderr)
            sys.exit(1)

        with open(ROUTES_JSON, "w") as f:
            json.dump(routes, f, indent=2)
            f.write("\n")

        print(f"Updated route '{args.route_id}' in {ROUTES_JSON}", file=sys.stderr)
    else:
        # Print coordinates to stdout
        print(json.dumps(simplified, indent=2))


if __name__ == "__main__":
    main()
