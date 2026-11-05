"""트램·지하철 노선 DB: trams.json(매주 GitHub Actions가 갱신)을 DB로 옮기고, 화면용 노선 데이터와
정류장 검색을 DB에서 제공합니다. 서버가 켜질 때 JSON 내용이 DB와 다르면(해시 비교) 새로 가져옵니다."""
import hashlib
import json
import pathlib
import unicodedata

from . import db as dbmod

DATA_FILE = pathlib.Path(__file__).resolve().parent / "static" / "data" / "trams.json"
SEARCH_LIMIT = 20

_lines_cache = {}  # data hash -> response dict


def normalize(text: str) -> str:
    """Lowercase, accents removed: 'Náměstí Míru' -> 'namesti miru' (Korean stays as is)."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", stripped).strip()


def _meta(conn, key):
    row = conn.execute("SELECT value FROM transit_meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def _set_meta(conn, key, value):
    conn.execute("DELETE FROM transit_meta WHERE key=?", (key,))
    conn.execute("INSERT INTO transit_meta (key, value) VALUES (?, ?)", (key, value))


def sync_from_file(path=DATA_FILE):
    """Import trams.json into the DB if its content changed. Returns True when it imported."""
    if not path.exists():
        print("[transit] no data file, skipping import", flush=True)
        return False
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    conn = dbmod.get_conn()
    try:
        if _meta(conn, "data_hash") == digest:
            return False
        data = json.loads(raw)
        routes, directions, stops = [], [], []
        groups = (("tram", data.get("routes", [])), ("metro", data.get("metro", [])))
        order = 0
        for mode, items in groups:
            for r in items:
                order += 1
                routes.append((r["id"], mode, r["name"], r.get("long_name", ""), r["color"], int(bool(r.get("night"))), order))
                for di, d in enumerate(r["directions"]):
                    directions.append((r["id"], di, d["headsign"], d.get("headsign_ko", ""), json.dumps(d["path"], separators=(",", ":"))))
                    for si, s in enumerate(d["stops"]):
                        ko = s.get("ko", "")
                        stops.append((r["id"], di, si, s["name"], ko, s["lat"], s["lng"], normalize(s["name"]) + " " + ko))
        # Replace everything in one transaction so readers never see half an import
        for table in ("transit_stops", "transit_directions", "transit_routes"):
            conn.execute(f"DELETE FROM {table}")
        conn.executemany("INSERT INTO transit_routes (id, mode, name, long_name, color, night, sort_order) VALUES (?,?,?,?,?,?,?)", routes)
        conn.executemany("INSERT INTO transit_directions (route_id, direction, headsign, headsign_ko, path) VALUES (?,?,?,?,?)", directions)
        conn.executemany("INSERT INTO transit_stops (route_id, direction, seq, name, name_ko, lat, lng, search) VALUES (?,?,?,?,?,?,?,?)", stops)
        _set_meta(conn, "data_hash", digest)
        _set_meta(conn, "valid_from", data.get("valid_from", ""))
        conn.commit()
        print(f"[transit] imported {len(routes)} routes, {len(stops)} stops", flush=True)
        return True
    finally:
        conn.close()


def lines():
    """All routes in the shape the transit page expects: {valid_from, routes: [trams], metro: [...]}."""
    conn = dbmod.get_conn()
    try:
        digest = _meta(conn, "data_hash")
        if digest in _lines_cache:
            return _lines_cache[digest]
        route_rows = conn.execute("SELECT * FROM transit_routes ORDER BY sort_order").fetchall()
        dir_rows = conn.execute("SELECT * FROM transit_directions ORDER BY route_id, direction").fetchall()
        stop_rows = conn.execute("SELECT route_id, direction, name, name_ko, lat, lng FROM transit_stops "
                                 "ORDER BY route_id, direction, seq").fetchall()
        valid_from = _meta(conn, "valid_from") or ""
    finally:
        conn.close()

    stops = {}
    for s in stop_rows:
        stops.setdefault((s["route_id"], s["direction"]), []).append(
            {"name": s["name"], "ko": s["name_ko"], "lat": s["lat"], "lng": s["lng"]})
    dirs = {}
    for d in dir_rows:
        dirs.setdefault(d["route_id"], []).append({
            "headsign": d["headsign"], "headsign_ko": d["headsign_ko"],
            "path": json.loads(d["path"]), "stops": stops.get((d["route_id"], d["direction"]), []),
        })
    out = {"valid_from": valid_from, "routes": [], "metro": []}
    for r in route_rows:
        out["routes" if r["mode"] == "tram" else "metro"].append({
            "id": r["id"], "name": r["name"], "long_name": r["long_name"], "color": r["color"],
            "night": bool(r["night"]), "directions": dirs.get(r["id"], []),
        })
    if digest:
        _lines_cache.clear()
        _lines_cache[digest] = out
    return out


def search_stops(query: str):
    """Stops whose Czech (accents optional) or Korean name contains the query, with the lines serving them."""
    q = normalize(query).replace("\\", "").replace("%", "").replace("_", "").strip()  # no LIKE wildcards from users
    if not q:
        return []
    like = "%" + q + "%"
    conn = dbmod.get_conn()
    try:
        rows = conn.execute(
            """SELECT s.name, s.name_ko, s.lat, s.lng, s.direction, r.id AS route_id, r.mode, r.name AS line,
                      r.color, r.night, r.sort_order
               FROM transit_stops s JOIN transit_routes r ON r.id = s.route_id
               WHERE s.search LIKE ?
               ORDER BY r.sort_order, s.direction, s.seq""",
            (like,),
        ).fetchall()
    finally:
        conn.close()

    found = {}
    for row in rows:
        stop = found.setdefault(row["name"], {
            "name": row["name"], "ko": row["name_ko"], "lat": row["lat"], "lng": row["lng"], "lines": [], "_seen": set(),
        })
        if row["route_id"] in stop["_seen"]:
            continue
        stop["_seen"].add(row["route_id"])
        stop["lines"].append({"id": row["route_id"], "mode": row["mode"], "name": row["line"],
                              "color": row["color"], "night": bool(row["night"]), "direction": row["direction"]})
    results = list(found.values())
    for s in results:
        del s["_seen"]
    # Names starting with the query first, then the rest alphabetically
    results.sort(key=lambda s: (not normalize(s["name"]).startswith(q) and not (s["ko"] or "").startswith(q), normalize(s["name"])))
    return results[:SEARCH_LIMIT]
