import os
import re
from urllib.parse import quote
import uuid
import pathlib

from starlette.responses import RedirectResponse
from starlette.routing import Route

from . import db as dbmod
from .auth_router import get_current_user
from .photo_gps import jpeg_gps
from .templating import templates

UPLOAD_DIR = pathlib.Path(__file__).resolve().parent / "static" / "uploads" / "places"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["맛집", "카페", "관광지", "숙소", "기타"]


def _back_url(request):
    """List page the visitor came from: /places (optionally filtered) or /favorites."""
    q = request.query_params
    if q.get("from") == "favorites":
        return "/favorites"
    if q.get("category") in CATEGORIES:
        return f"/places?category={quote(q['category'])}"
    return "/places"


def parse_coords(form):
    """Map-picked lat/lng from the form, or None if missing/invalid."""
    try:
        lat, lng = float(form.get("lat")), float(form.get("lng"))
    except (TypeError, ValueError):
        return None
    return (lat, lng) if -90 <= lat <= 90 and -180 <= lng <= 180 else None


PENDING_PHOTO_RE = re.compile(r"^[0-9a-f]{32}\.jpe?g$")


def _detail_url(request, place_id):
    # Keep the list context (?category= / ?from=) across review/favorite posts
    qs = request.url.query
    return f"/places/{place_id}" + (f"?{qs}" if qs else "")


def _place_with_stats(conn, place_id):
    place = conn.execute("SELECT * FROM places WHERE id=?", (place_id,)).fetchone()
    if not place:
        return None
    stats = conn.execute(
        "SELECT COUNT(*) as cnt, AVG(rating) as avg FROM place_reviews WHERE place_id=?", (place_id,)
    ).fetchone()
    reviews = conn.execute(
        """SELECT place_reviews.*, users.nickname FROM place_reviews
           JOIN users ON users.id = place_reviews.user_id
           WHERE place_id=? ORDER BY place_reviews.created_at DESC""",
        (place_id,),
    ).fetchall()
    return {
        "place": place,
        "review_count": stats["cnt"],
        "avg_rating": round(stats["avg"], 1) if stats["avg"] else None,
        "reviews": reviews,
    }


async def places_list(request):
    user = get_current_user(request)
    category = request.query_params.get("category")
    conn = dbmod.get_conn()
    if category and category in CATEGORIES:
        rows = conn.execute(
            "SELECT * FROM places WHERE category=? ORDER BY created_at DESC", (category,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM places ORDER BY created_at DESC").fetchall()

    places = []
    for r in rows:
        stats = conn.execute(
            "SELECT COUNT(*) as cnt, AVG(rating) as avg FROM place_reviews WHERE place_id=?", (r["id"],)
        ).fetchone()
        places.append({"place": r, "review_count": stats["cnt"], "avg_rating": round(stats["avg"], 1) if stats["avg"] else None})
    conn.close()

    return templates.TemplateResponse(
        request, "places_list.html",
        {"active": "places", "user": user, "places": places, "categories": CATEGORIES, "selected_category": category},
    )


async def place_detail(request):
    user = get_current_user(request)
    place_id = int(request.path_params["place_id"])
    conn = dbmod.get_conn()
    data = _place_with_stats(conn, place_id)
    if not data:
        conn.close()
        return RedirectResponse(url="/places", status_code=303)

    is_favorite = False
    if user:
        fav = conn.execute(
            "SELECT id FROM favorites WHERE user_id=? AND place_id=?", (user["id"], place_id)
        ).fetchone()
        is_favorite = fav is not None
    conn.close()

    data.update({"active": "places", "user": user, "is_favorite": is_favorite,
                 "back_url": _back_url(request), "list_qs": request.url.query})
    return templates.TemplateResponse(request, "place_detail.html", data)


async def place_new_get(request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "place_new.html", {"active": "places", "user": user, "categories": CATEGORIES})


async def place_new_post(request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    name = (form.get("name") or "").strip()
    category = form.get("category") if form.get("category") in CATEGORIES else "기타"
    description = (form.get("description") or "").strip()
    photo = form.get("photo")

    photo_token = form.get("photo_token") or ""
    ctx = {"active": "places", "user": user, "categories": CATEGORIES,
           "values": {"name": name, "category": category, "description": description}}

    def fail(msg, **extra):
        ctx.update(flash=msg, flash_type="error", **extra)
        return templates.TemplateResponse(request, "place_new.html", ctx)

    if photo_token:
        # Re-submit: the photo was kept from the first attempt
        if not PENDING_PHOTO_RE.match(photo_token) or not (UPLOAD_DIR / photo_token).exists():
            return fail("사진을 다시 올려주세요.")
        fname, gps = photo_token, jpeg_gps((UPLOAD_DIR / photo_token).read_bytes())
    else:
        if photo is None or not getattr(photo, "filename", None):
            return fail("사진을 올려주세요.")
        ext = pathlib.Path(photo.filename).suffix.lower()
        if ext not in (".jpg", ".jpeg"):
            return fail("JPG 사진을 올려주세요.")
        content = await photo.read()
        fname = f"{uuid.uuid4().hex}{ext}"
        gps = jpeg_gps(content)
        # Save right away so later validation errors don't make the visitor re-upload
        (UPLOAD_DIR / fname).write_bytes(content)

    coords = gps or parse_coords(form)
    if coords and not gps:
        ctx["values"].update(lat=coords[0], lng=coords[1])
    if not name:
        return fail("장소 이름을 입력해주세요.", need_location=not coords, photo_token=fname)
    if not coords:
        # ponytail: a pending photo is left in uploads if the visitor abandons this step; sweep old unreferenced files if it piles up
        return fail("사진에서 위치 정보를 찾지 못했어요. 아래에서 장소를 검색하거나 지도를 눌러 위치를 표시해주세요.",
                    need_location=True, photo_token=fname)
    lat_f, lng_f = coords
    photo_path = f"/static/uploads/places/{fname}"

    conn = dbmod.get_conn()
    conn.execute(
        """INSERT INTO places (user_id, name, category, lat, lng, description, photo_path, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (user["id"], name, category, lat_f, lng_f, description, photo_path, dbmod.now()),
    )
    conn.commit()
    place_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    conn.close()

    return RedirectResponse(url=f"/places/{place_id}", status_code=303)


async def place_review_post(request):
    user = get_current_user(request)
    place_id = int(request.path_params["place_id"])
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    try:
        rating = int(form.get("rating"))
        assert 1 <= rating <= 5
    except (TypeError, ValueError, AssertionError):
        rating = 5
    comment = (form.get("comment") or "").strip()

    conn = dbmod.get_conn()
    conn.execute(
        "INSERT INTO place_reviews (place_id, user_id, rating, comment, created_at) VALUES (?,?,?,?,?)",
        (place_id, user["id"], rating, comment, dbmod.now()),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url=_detail_url(request, place_id), status_code=303)


async def place_favorite_toggle(request):
    user = get_current_user(request)
    place_id = int(request.path_params["place_id"])
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = dbmod.get_conn()
    existing = conn.execute(
        "SELECT id FROM favorites WHERE user_id=? AND place_id=?", (user["id"], place_id)
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM favorites WHERE id=?", (existing["id"],))
    else:
        conn.execute(
            "INSERT INTO favorites (user_id, place_id, created_at) VALUES (?,?,?)",
            (user["id"], place_id, dbmod.now()),
        )
    conn.commit()
    conn.close()
    return RedirectResponse(url=_detail_url(request, place_id), status_code=303)


async def favorites_list(request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = dbmod.get_conn()
    rows = conn.execute(
        """SELECT places.* FROM favorites
           JOIN places ON places.id = favorites.place_id
           WHERE favorites.user_id=? ORDER BY favorites.created_at DESC""",
        (user["id"],),
    ).fetchall()
    places = []
    for r in rows:
        stats = conn.execute(
            "SELECT COUNT(*) as cnt, AVG(rating) as avg FROM place_reviews WHERE place_id=?", (r["id"],)
        ).fetchone()
        places.append({"place": r, "review_count": stats["cnt"], "avg_rating": round(stats["avg"], 1) if stats["avg"] else None})
    conn.close()

    return templates.TemplateResponse(request, "favorites.html", {"active": "favorites", "user": user, "places": places})


routes = [
    Route("/places", places_list, methods=["GET"]),
    Route("/places/new", place_new_get, methods=["GET"]),
    Route("/places/new", place_new_post, methods=["POST"]),
    Route("/places/{place_id:int}", place_detail, methods=["GET"]),
    Route("/places/{place_id:int}/review", place_review_post, methods=["POST"]),
    Route("/places/{place_id:int}/favorite", place_favorite_toggle, methods=["POST"]),
    Route("/favorites", favorites_list, methods=["GET"]),
]
