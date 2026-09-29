from starlette.routing import Route

from . import journal_data as data
from .auth_router import get_current_user
from .templating import templates


async def journal(request):
    return templates.TemplateResponse(request, "journal.html", {
        "active": "journal",
        "user": get_current_user(request),
        "days": data.DAYS,
        "trip_end": data.TRIP_END,
        "album_tabs": data.ALBUM_TABS,
        "album": data.ALBUM,
        "gallery": data.GALLERY,
    })


routes = [
    Route("/journal", journal),
]
