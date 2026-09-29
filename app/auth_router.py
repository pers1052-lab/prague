from starlette.responses import RedirectResponse
from starlette.routing import Route

from . import db as dbmod
from .auth import hash_password, verify_password, make_session_cookie
from .templating import templates

SESSION_COOKIE = "session"


def get_current_user(request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    from .auth import read_session_cookie
    user_id = read_session_cookie(token)
    if not user_id:
        return None
    conn = dbmod.get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row


async def register_get(request):
    return templates.TemplateResponse(request, "register.html", {"active": "register", "user": get_current_user(request)})


async def register_post(request):
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    nickname = (form.get("nickname") or "").strip()

    ctx = {"active": "register", "user": None}
    if not email or not password or not nickname:
        ctx["flash"] = "모든 항목을 입력해주세요."
        ctx["flash_type"] = "error"
        return templates.TemplateResponse(request, "register.html", ctx)
    if len(password) < 6:
        ctx["flash"] = "비밀번호는 6자 이상이어야 합니다."
        ctx["flash_type"] = "error"
        return templates.TemplateResponse(request, "register.html", ctx)

    conn = dbmod.get_conn()
    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.close()
        ctx["flash"] = "이미 가입된 이메일입니다."
        ctx["flash_type"] = "error"
        return templates.TemplateResponse(request, "register.html", ctx)

    pw_hash, salt = hash_password(password)
    conn.execute(
        "INSERT INTO users (email, password_hash, salt, nickname, created_at) VALUES (?,?,?,?,?)",
        (email, pw_hash, salt, nickname, dbmod.now()),
    )
    conn.commit()
    user_id = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
    conn.close()

    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(SESSION_COOKIE, make_session_cookie(user_id), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 14)
    return resp


async def login_get(request):
    return templates.TemplateResponse(request, "login.html", {"active": "login", "user": get_current_user(request)})


async def login_post(request):
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""

    conn = dbmod.get_conn()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()

    if not row or not verify_password(password, row["salt"], row["password_hash"]):
        return templates.TemplateResponse(
            request, "login.html",
            {"active": "login", "user": None, "flash": "이메일 또는 비밀번호가 올바르지 않습니다.", "flash_type": "error"},
        )

    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(SESSION_COOKIE, make_session_cookie(row["id"]), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 14)
    return resp


async def logout(request):
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


routes = [
    Route("/register", register_get, methods=["GET"]),
    Route("/register", register_post, methods=["POST"]),
    Route("/login", login_get, methods=["GET"]),
    Route("/login", login_post, methods=["POST"]),
    Route("/logout", logout, methods=["GET"]),
]
