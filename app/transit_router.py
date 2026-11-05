from starlette.responses import JSONResponse
from starlette.routing import Route

from . import transit_data
from .auth_router import get_current_user
from .templating import asset, templates


async def transit_page(request):
    user = get_current_user(request)
    # Versioned like the static files, so a weekly data refresh is fetched fresh after deploy
    lines_url = "/api/transit/lines?" + asset("data/trams.json").partition("?")[2]
    return templates.TemplateResponse(request, "transit.html", {"active": "transit", "user": user, "lines_url": lines_url})


async def lines_api(request):
    return JSONResponse(transit_data.lines(), headers={"Cache-Control": "public, max-age=3600"})


async def stop_search_api(request):
    q = (request.query_params.get("q") or "").strip()[:50]
    return JSONResponse({"query": q, "stops": transit_data.search_stops(q)})


routes = [
    Route("/transit", transit_page, methods=["GET"]),
    Route("/api/transit/lines", lines_api, methods=["GET"]),
    Route("/api/transit/stops", stop_search_api, methods=["GET"]),
]
