from starlette.routing import Route

from . import db as dbmod
from .auth_router import get_current_user
from .email_service import send_inquiry_email
from .templating import templates


async def inquiry_get(request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "inquiry.html", {"active": "inquiry", "user": user})


async def inquiry_post(request):
    user = get_current_user(request)
    form = await request.form()
    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip()
    message = (form.get("message") or "").strip()

    ctx = {"active": "inquiry", "user": user}
    if not name or not email or not message:
        ctx["flash"] = "모든 항목을 입력해주세요."
        ctx["flash_type"] = "error"
        return templates.TemplateResponse(request, "inquiry.html", ctx)

    sent, detail = send_inquiry_email(name, email, message)

    conn = dbmod.get_conn()
    conn.execute(
        "INSERT INTO inquiries (name, email, message, created_at, email_sent) VALUES (?,?,?,?,?)",
        (name, email, message, dbmod.now(), 1 if sent else 0),
    )
    conn.commit()
    conn.close()

    ctx["flash"] = "문의가 접수되었습니다. 빠르게 답변 드리겠습니다." if sent else "문의가 저장되었습니다. (이메일 발송은 서버에 SMTP가 설정되면 자동으로 활성화됩니다)"
    ctx["flash_type"] = "ok"
    return templates.TemplateResponse(request, "inquiry.html", ctx)


routes = [
    Route("/inquiry", inquiry_get, methods=["GET"]),
    Route("/inquiry", inquiry_post, methods=["POST"]),
]
