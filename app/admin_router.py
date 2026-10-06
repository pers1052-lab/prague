"""관리자 전용: 문의 내역 보기/삭제, 장소·리뷰 수정/삭제. 모든 핸들러가 서버에서 관리자 여부를 확인합니다."""
import pathlib
import uuid

from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route

from . import db as dbmod
from .auth import is_admin
from .auth_router import get_current_user
from .places_router import CATEGORIES, UPLOAD_DIR, parse_coords
from .templating import templates


def remove_upload(photo_path):
    # Only user uploads are removed; journal media stays (the journal still uses it)
    path = photo_path or ""
    if path.startswith("/static/uploads/places/"):
        (UPLOAD_DIR / path.rsplit("/", 1)[1]).unlink(missing_ok=True)


def require_admin(request):
    """The admin user, or a response to return instead (login redirect / 403)."""
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse(url="/login", status_code=303)
    if not is_admin(user):
        return None, PlainTextResponse("관리자만 접근할 수 있습니다.", status_code=403)
    return user, None


# ---------- 문의 ----------

async def admin_home(request):
    user, deny = require_admin(request)
    if deny:
        return deny
    conn = dbmod.get_conn()
    inquiries = conn.execute("SELECT * FROM inquiries ORDER BY created_at DESC").fetchall()
    conn.close()
    return templates.TemplateResponse(request, "admin.html", {
        "active": "admin", "user": user, "inquiries": inquiries,
        "flash": "삭제했습니다." if request.query_params.get("deleted") else None,
    })


async def inquiry_delete(request):
    user, deny = require_admin(request)
    if deny:
        return deny
    conn = dbmod.get_conn()
    conn.execute("DELETE FROM inquiries WHERE id=?", (request.path_params["inquiry_id"],))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin?deleted=1", status_code=303)


# ---------- 장소 ----------

async def place_edit(request):
    user, deny = require_admin(request)
    if deny:
        return deny
    place_id = request.path_params["place_id"]
    conn = dbmod.get_conn()
    place = conn.execute("SELECT * FROM places WHERE id=?", (place_id,)).fetchone()
    if not place:
        conn.close()
        return RedirectResponse(url="/places", status_code=303)

    ctx = {"active": "places", "user": user, "place": place, "categories": CATEGORIES}
    if request.method == "POST":
        form = await request.form()
        name = (form.get("name") or "").strip()
        category = form.get("category") if form.get("category") in CATEGORIES else place["category"]
        description = (form.get("description") or "").strip()
        coords = parse_coords(form) or (place["lat"], place["lng"])
        photo = form.get("photo")
        has_photo = photo is not None and getattr(photo, "filename", None)
        ext = pathlib.Path(photo.filename).suffix.lower() if has_photo else ""
        error = ("장소 이름을 입력해주세요." if not name
                 else "JPG 사진을 올려주세요." if has_photo and ext not in (".jpg", ".jpeg") else None)
        if error:
            conn.close()
            ctx.update(flash=error, flash_type="error")
            return templates.TemplateResponse(request, "place_edit.html", ctx)
        photo_path = place["photo_path"]
        if has_photo:
            fname = f"{uuid.uuid4().hex}{ext}"
            (UPLOAD_DIR / fname).write_bytes(await photo.read())
            photo_path = f"/static/uploads/places/{fname}"
        conn.execute(
            "UPDATE places SET name=?, category=?, description=?, lat=?, lng=?, photo_path=? WHERE id=?",
            (name, category, description, coords[0], coords[1], photo_path, place_id),
        )
        conn.commit()
        conn.close()
        if photo_path != place["photo_path"]:
            remove_upload(place["photo_path"])
        return RedirectResponse(url=f"/places/{place_id}", status_code=303)

    conn.close()
    return templates.TemplateResponse(request, "place_edit.html", ctx)


async def place_delete(request):
    user, deny = require_admin(request)
    if deny:
        return deny
    place_id = request.path_params["place_id"]
    conn = dbmod.get_conn()
    place = conn.execute("SELECT photo_path FROM places WHERE id=?", (place_id,)).fetchone()
    if place:
        conn.execute("DELETE FROM place_reviews WHERE place_id=?", (place_id,))
        conn.execute("DELETE FROM favorites WHERE place_id=?", (place_id,))
        conn.execute("DELETE FROM places WHERE id=?", (place_id,))
        conn.commit()
        remove_upload(place["photo_path"])
    conn.close()
    return RedirectResponse(url="/places", status_code=303)


# ---------- 리뷰 ----------

async def review_edit(request):
    user, deny = require_admin(request)
    if deny:
        return deny
    review_id = request.path_params["review_id"]
    conn = dbmod.get_conn()
    review = conn.execute(
        """SELECT place_reviews.*, places.name AS place_name, users.nickname FROM place_reviews
           JOIN places ON places.id = place_reviews.place_id
           JOIN users ON users.id = place_reviews.user_id WHERE place_reviews.id=?""",
        (review_id,),
    ).fetchone()
    if not review:
        conn.close()
        return RedirectResponse(url="/places", status_code=303)

    if request.method == "POST":
        form = await request.form()
        try:
            rating = int(form.get("rating"))
        except (TypeError, ValueError):
            rating = review["rating"]
        rating = min(5, max(1, rating))
        conn.execute("UPDATE place_reviews SET rating=?, comment=? WHERE id=?",
                     (rating, (form.get("comment") or "").strip(), review_id))
        conn.commit()
        conn.close()
        return RedirectResponse(url=f"/places/{review['place_id']}", status_code=303)

    conn.close()
    return templates.TemplateResponse(request, "review_edit.html", {"active": "places", "user": user, "review": review})


async def review_delete(request):
    user, deny = require_admin(request)
    if deny:
        return deny
    review_id = request.path_params["review_id"]
    conn = dbmod.get_conn()
    row = conn.execute("SELECT place_id FROM place_reviews WHERE id=?", (review_id,)).fetchone()
    conn.execute("DELETE FROM place_reviews WHERE id=?", (review_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/places/{row['place_id']}" if row else "/places", status_code=303)


routes = [
    Route("/admin", admin_home, methods=["GET"]),
    Route("/admin/inquiries/{inquiry_id:int}/delete", inquiry_delete, methods=["POST"]),
    Route("/places/{place_id:int}/edit", place_edit, methods=["GET", "POST"]),
    Route("/places/{place_id:int}/delete", place_delete, methods=["POST"]),
    Route("/reviews/{review_id:int}/edit", review_edit, methods=["GET", "POST"]),
    Route("/reviews/{review_id:int}/delete", review_delete, methods=["POST"]),
]
