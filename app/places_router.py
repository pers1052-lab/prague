import os
import uuid
import pathlib

from starlette.responses import RedirectResponse
from starlette.routing import Route

from . import db as dbmod
from .auth_router import get_current_user
from .templating import templates

UPLOAD_DIR = pathlib.Path(__file__).resolve().parent / "static" / "uploads" / "places"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["맛집", "카페", "관광지", "숙소", "기타"]


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

    data.update({"active": "places", "user": user, "is_favorite": is_favorite})
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
    category = form.get("category") or "기타"
    lat = form.get("lat")
    lng = form.get("lng")
    description = (form.get("description") or "").strip()
    photo = form.get("photo")

    ctx = {"active": "places", "user": user, "categories": CATEGORIES}
    try:
        lat_f, lng_f = float(lat), float(lng)
    except (TypeError, ValueError):
        ctx["flash"] = "위도/경도를 올바르게 입력해주세요."
        ctx["flash_type"] = "error"
        return templates.TemplateResponse(request, "place_new.html", ctx)

    if not name:
        ctx["flash"] = "장소 이름을 입력해주세요."
        ctx["flash_type"] = "error"
        return templates.TemplateResponse(request, "place_new.html", ctx)

    photo_path = None
    if photo is not None and getattr(photo, "filename", None):
        ext = pathlib.Path(photo.filename).suffix.lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            fname = f"{uuid.uuid4().hex}{ext}"
            dest = UPLOAD_DIR / fname
            content = await photo.read()
            dest.write_bytes(content)
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
    return RedirectResponse(url=f"/places/{place_id}", status_code=303)


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
    return RedirectResponse(url=f"/places/{place_id}", status_code=303)


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
