from starlette.routing import Route

from .auth_router import get_current_user
from .templating import templates


async def transit_page(request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "transit.html", {"active": "transit", "user": user})


routes = [
    Route("/transit", transit_page, methods=["GET"]),
]
