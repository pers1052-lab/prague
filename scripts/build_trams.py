"""PID(프라하 대중교통) GTFS에서 지금 운행 중인 트램 노선을 뽑아 교통정보 화면용 JSON을 만듭니다.

    python scripts/build_trams.py PID_GTFS.zip app/static/data/trams.json

GTFS 원본: https://data.pid.cz/PID_GTFS.zip (GitHub Actions가 매주 받아서 실행합니다)
노선마다 방향별로 가장 많이 다니는 경로(shape) 하나를 골라 정류장 순서와 경로 좌표를 저장합니다.
표준 라이브러리만 사용하고, 큰 파일(stop_times, shapes)은 한 줄씩 읽어 메모리를 적게 씁니다.
"""
import collections
import csv
import datetime
import io
import json
import sys
import zipfile

TRAM_ROUTE_TYPE = "0"
ACTIVE_WINDOW_DAYS = 7      # 이 기간 안에 한 번이라도 운행하면 "현재 운행 중"
PATH_TOLERANCE = 0.00003    # 경로 단순화 허용 오차(도), 약 3m
FREQUENT_SHARE = 0.4        # 가장 많이 다니는 경로의 40% 이상 운행하면 "주요 경로"로 보고, 그중 가장 긴 것을 고름


def read(zf, name):
    with zf.open(name) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", newline=""))


def active_services(zf, today):
    days = [today + datetime.timedelta(days=i) for i in range(ACTIVE_WINDOW_DAYS)]
    weekday_cols = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    names = set(zf.namelist())
    running = collections.defaultdict(set)  # service_id -> set of dates
    if "calendar.txt" in names:
        for row in read(zf, "calendar.txt"):
            start = datetime.datetime.strptime(row["start_date"], "%Y%m%d").date()
            end = datetime.datetime.strptime(row["end_date"], "%Y%m%d").date()
            for d in days:
                if start <= d <= end and row[weekday_cols[d.weekday()]] == "1":
                    running[row["service_id"]].add(d)
    if "calendar_dates.txt" in names:
        for row in read(zf, "calendar_dates.txt"):
            d = datetime.datetime.strptime(row["date"], "%Y%m%d").date()
            if d in days:
                (running[row["service_id"]].add if row["exception_type"] == "1"
                 else running[row["service_id"]].discard)(d)
    return {sid for sid, ds in running.items() if ds}


def simplify(points, tol=PATH_TOLERANCE):
    """Ramer-Douglas-Peucker: drop points that sit (almost) on the line between neighbours."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (ay, ax), (by, bx) = points[a], points[b]
        dy, dx = by - ay, bx - ax
        norm = (dx * dx + dy * dy) ** 0.5
        far, far_d = None, tol
        for i in range(a + 1, b):
            py, px = points[i]
            d = (abs(dx * (ay - py) - dy * (ax - px)) / norm) if norm else ((py - ay) ** 2 + (px - ax) ** 2) ** 0.5
            if d > far_d:
                far, far_d = i, d
        if far is not None:
            keep[far] = True
            stack += [(a, far), (far, b)]
    return [p for p, k in zip(points, keep) if k]


def route_sort_key(name):
    return (0, int(name), "") if name.isdigit() else (1, 0, name)


def build(gtfs_path, today=None):
    today = today or datetime.date.today()
    zf = zipfile.ZipFile(gtfs_path)

    routes = {r["route_id"]: r for r in read(zf, "routes.txt") if r["route_type"] == TRAM_ROUTE_TYPE}
    services = active_services(zf, today)

    # (route, direction) -> shape -> [trip count, sample trip, headsign]
    variants = collections.defaultdict(dict)
    for t in read(zf, "trips.txt"):
        if t["route_id"] not in routes or t["service_id"] not in services:
            continue
        key = (t["route_id"], t.get("direction_id") or "0")
        shape = t.get("shape_id") or ("trip:" + t["trip_id"])
        v = variants[key].setdefault(shape, [0, t["trip_id"], t.get("trip_headsign", "")])
        v[0] += 1

    # Frequent variants per direction; short-turn trips (e.g. to a depot) can outnumber
    # full-length ones, so among the frequent ones the longest stop sequence wins.
    candidates = {}
    for key, shapes in variants.items():
        top = max(v[0] for v in shapes.values())
        candidates[key] = [(shape, v) for shape, v in shapes.items() if v[0] >= top * FREQUENT_SHARE]
    sample_trips = {v[1] for cands in candidates.values() for _, v in cands}

    trip_stops = collections.defaultdict(list)
    for st in read(zf, "stop_times.txt"):
        if st["trip_id"] in sample_trips:
            trip_stops[st["trip_id"]].append((int(st["stop_sequence"]), st["stop_id"]))

    chosen = {}  # (route, direction) -> (shape_id, trip_id, headsign)
    for key, cands in candidates.items():
        shape, (count, trip_id, headsign) = max(cands, key=lambda c: (len(trip_stops[c[1][1]]), c[1][0]))
        chosen[key] = (shape, trip_id, headsign)
    want_shapes = {shape for shape, _, _ in chosen.values()}

    stop_ids = {sid for seq in trip_stops.values() for _, sid in seq}
    stops = {s["stop_id"]: (s["stop_name"], round(float(s["stop_lat"]), 6), round(float(s["stop_lon"]), 6))
             for s in read(zf, "stops.txt") if s["stop_id"] in stop_ids}

    shape_pts = collections.defaultdict(list)
    if "shapes.txt" in zf.namelist():
        for p in read(zf, "shapes.txt"):
            if p["shape_id"] in want_shapes:
                shape_pts[p["shape_id"]].append((int(p["shape_pt_sequence"]), float(p["shape_pt_lat"]), float(p["shape_pt_lon"])))

    out = []
    for route_id, r in routes.items():
        directions = []
        for direction in ("0", "1"):
            if (route_id, direction) not in chosen:
                continue
            shape, trip_id, headsign = chosen[(route_id, direction)]
            seq = [stops[sid] for _, sid in sorted(trip_stops[trip_id]) if sid in stops]
            if not seq:
                continue
            pts = [(lat, lng) for _, lat, lng in sorted(shape_pts.get(shape, []))] or [(la, ln) for _, la, ln in seq]
            path = [[round(lat, 5), round(lng, 5)] for lat, lng in simplify(pts)]
            directions.append({
                "headsign": headsign or seq[-1][0],
                "stops": [{"name": n, "lat": la, "lng": ln} for n, la, ln in seq],
                "path": path,
            })
        if not directions:
            continue  # 이번 주에 운행하지 않는 노선
        name = r.get("route_short_name") or route_id
        color = (r.get("route_color") or "").strip()
        out.append({
            "id": route_id,
            "name": name,
            "long_name": r.get("route_long_name", ""),
            "color": "#" + color if color else "#7A0603",
            "night": name.isdigit() and 90 <= int(name) <= 99,
            "directions": directions,
        })
    out.sort(key=lambda r: route_sort_key(r["name"]))

    feed = {}
    if "feed_info.txt" in zf.namelist():
        feed = next(read(zf, "feed_info.txt"), {})
    return {
        "source": "PID GTFS (data.pid.cz)",
        "feed_version": feed.get("feed_version", ""),
        "valid_from": today.isoformat(),
        "routes": out,
    }


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data = build(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(data['routes'])} tram routes -> {sys.argv[2]}")
    print(" ".join(r["name"] for r in data["routes"]))


if __name__ == "__main__":
    main()
