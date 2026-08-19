#!/usr/bin/env python3
"""
Convert a location history JSON file into a route for routes.json.

Usage:
  python location_to_route.py <location_history.json> [--route-id ID] [--update]

Two input formats are supported and detected automatically:

1. Location History Visualizer output — an array of:
     { "lat": number, "lng": number, "timestamp": string }

2. Google Timeline export ("Timeline.json" from Android/iOS) — an array of
   segments keyed by startTime/endTime, each holding one of `timelinePath`
   (dense track points), `visit` (a dwell) or `activity` (a leg). Positions
   are "geo:lat,lng" strings.

Options:
  --route-id ID   The route ID in routes.json to update or create
  --update        Write the route into routes.json (creates it if missing)
  --start DATE    Keep points on or after this local date (YYYY-MM-DD)
  --end DATE      Keep points on or before this local date (YYYY-MM-DD)
  --tz-offset H   Hours from UTC used to derive local dates (default: -7)
  --name/--description/--color/--tags/--date  Metadata for a newly created route

Without --update, prints the coordinates array to stdout.
"""
import json
import sys
import math
import argparse
from datetime import datetime, timedelta, timezone
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


def rdp(points, epsilon_m, lat_scale):
    """
    Ramer-Douglas-Peucker simplification. Keeps the points that define the
    shape of the line and drops the ones that sit on a straight run, so
    switchbacks survive a low point budget where distance-thinning would
    cut the corner.

    Coordinates are treated as a local equirectangular plane: degrees of
    latitude are a constant 111,320 m, and degrees of longitude are scaled
    by cos(latitude) via lat_scale.
    """
    if len(points) <= 2:
        return points

    M = 111320.0

    def perp_distance(pt, start, end):
        x, y = (pt[1] - start[1]) * lat_scale * M, (pt[0] - start[0]) * M
        ex, ey = (end[1] - start[1]) * lat_scale * M, (end[0] - start[0]) * M
        seg = math.hypot(ex, ey)
        if seg == 0:
            return math.hypot(x, y)
        return abs(x * ey - y * ex) / seg

    # Iterative to avoid blowing the recursion limit on long tracks.
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        worst, worst_i = 0.0, None
        for i in range(lo + 1, hi):
            d = perp_distance(points[i], points[lo], points[hi])
            if d > worst:
                worst, worst_i = d, i
        if worst_i is not None and worst > epsilon_m:
            keep[worst_i] = True
            stack.append((lo, worst_i))
            stack.append((worst_i, hi))

    return [p for p, k in zip(points, keep) if k]


def simplify_route(points, min_distance_m=500, max_points=200, epsilon_m=0):
    """
    Simplify a route: drop points closer together than min_distance_m (which
    also collapses the GPS jitter of a long dwell), then run Douglas-Peucker
    at epsilon_m to strip points that fall on a straight run.

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

    if epsilon_m > 0:
        mean_lat = sum(p[0] for p in simplified) / len(simplified)
        simplified = rdp(simplified, epsilon_m, math.cos(math.radians(mean_lat)))

    # If still too many points, subsample evenly
    if len(simplified) > max_points:
        step = len(simplified) / max_points
        resampled = []
        for i in range(max_points - 1):
            resampled.append(simplified[int(i * step)])
        resampled.append(simplified[-1])
        simplified = resampled

    return simplified


def parse_time(ts):
    """Parse an ISO-8601 timestamp into an aware datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def parse_geo(value):
    """Parse a 'geo:lat,lng' string into a (lat, lng) tuple."""
    if not isinstance(value, str) or not value.startswith("geo:"):
        return None
    try:
        lat, lng = value[4:].split(",")
        return float(lat), float(lng)
    except ValueError:
        return None


def extract_timeline(data):
    """Pull (datetime, lat, lng) points out of a Google Timeline export."""
    points = []
    for entry in data:
        try:
            start = parse_time(entry["startTime"])
            end = parse_time(entry["endTime"])
        except (KeyError, ValueError):
            continue

        if "timelinePath" in entry:
            for p in entry["timelinePath"]:
                coord = parse_geo(p.get("point"))
                if coord:
                    offset = float(p.get("durationMinutesOffsetFromStartTime", 0))
                    points.append((start + timedelta(minutes=offset),) + coord)
        elif "visit" in entry:
            coord = parse_geo(entry["visit"].get("topCandidate", {}).get("placeLocation"))
            if coord:
                points.append((start,) + coord)
        elif "activity" in entry:
            for key, when in (("start", start), ("end", end)):
                coord = parse_geo(entry["activity"].get(key))
                if coord:
                    points.append((when,) + coord)

    return points


def extract_visualizer(data):
    """Pull (datetime, lat, lng) points out of Location History Visualizer output."""
    points = []
    for entry in data:
        lat, lng = entry.get("lat"), entry.get("lng")
        if lat is None or lng is None:
            continue
        try:
            when = parse_time(entry.get("timestamp", ""))
        except ValueError:
            continue
        points.append((when, float(lat), float(lng)))
    return points


def load_location_history(path, start_date=None, end_date=None, tz_offset=-7):
    """Load a location history file and return [lat, lng, timestamp] triples."""
    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Error: expected a JSON array", file=sys.stderr)
        sys.exit(1)

    if data and "startTime" in data[0]:
        points = extract_timeline(data)
    else:
        points = extract_visualizer(data)

    # Dates are interpreted in a fixed local zone so a trip's days line up with
    # the calendar the traveller experienced, not UTC.
    local = timezone(timedelta(hours=tz_offset))
    if start_date:
        lo = datetime.fromisoformat(start_date).replace(tzinfo=local)
        points = [p for p in points if p[0] >= lo]
    if end_date:
        hi = datetime.fromisoformat(end_date).replace(tzinfo=local) + timedelta(days=1)
        points = [p for p in points if p[0] < hi]

    points.sort(key=lambda p: p[0])

    return [[round(p[1], 6), round(p[2], 6),
             p[0].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")]
            for p in points]


def main():
    parser = argparse.ArgumentParser(description="Convert location history to route coordinates")
    parser.add_argument("input", help="Path to location history JSON file")
    parser.add_argument("--route-id", help="Route ID to update in routes.json")
    parser.add_argument("--update", action="store_true", help="Update routes.json in place")
    parser.add_argument("--min-distance", type=int, default=500,
                        help="Minimum distance in meters between points (default: 500)")
    parser.add_argument("--max-points", type=int, default=200,
                        help="Maximum number of points to keep (default: 200)")
    parser.add_argument("--epsilon", type=int, default=0,
                        help="Douglas-Peucker tolerance in meters; 0 disables it (default: 0)")
    parser.add_argument("--start", help="Keep points on or after this local date (YYYY-MM-DD)")
    parser.add_argument("--end", help="Keep points on or before this local date (YYYY-MM-DD)")
    parser.add_argument("--tz-offset", type=int, default=-7,
                        help="Hours from UTC used to derive local dates (default: -7)")
    parser.add_argument("--name", help="Display name for a newly created route")
    parser.add_argument("--description", help="Description for a newly created route")
    parser.add_argument("--color", help="Line color for a newly created route")
    parser.add_argument("--tags", help="Comma-separated tags for a newly created route")
    parser.add_argument("--date", help="Sort date (YYYY-MM-DD) for a newly created route")
    args = parser.parse_args()

    # Load and simplify
    raw_points = load_location_history(args.input, args.start, args.end, args.tz_offset)
    print(f"Loaded {len(raw_points)} raw points", file=sys.stderr)
    if not raw_points:
        print("Error: no points in range", file=sys.stderr)
        sys.exit(1)
    print(f"Range: {raw_points[0][2]} -> {raw_points[-1][2]}", file=sys.stderr)

    simplified = simplify_route(raw_points,
                                min_distance_m=args.min_distance,
                                max_points=args.max_points,
                                epsilon_m=args.epsilon)
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

        if found:
            action = "Updated"
        else:
            action = "Created"
            routes.append({
                "id": args.route_id,
                "name": args.name or args.route_id,
                "description": args.description or "",
                "date": args.date or simplified[0][2][:10],
                "tags": [t.strip() for t in args.tags.split(",")] if args.tags else [],
                "color": args.color or "#3388ff",
                "coordinates": simplified,
            })

        with open(ROUTES_JSON, "w") as f:
            json.dump(routes, f, indent=2)
            f.write("\n")

        print(f"{action} route '{args.route_id}' in {ROUTES_JSON}", file=sys.stderr)
    else:
        # Print coordinates to stdout
        print(json.dumps(simplified, indent=2))


if __name__ == "__main__":
    main()
