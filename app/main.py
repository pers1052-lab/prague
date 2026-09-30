import pathlib
import contextlib

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from . import db as dbmod
from . import seed_places
from .templating import templates
from .auth_router import get_current_user, routes as auth_routes
from .journal_router import routes as journal_routes
from .places_router import routes as places_routes
from .inquiry_router import routes as inquiry_routes
from .transit_router import routes as transit_routes
from .admin_router import routes as admin_routes

STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"


async def home(request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "home.html", {"active": "home", "user": user})


@contextlib.asynccontextmanager
async def lifespan(app):
    dbmod.init_db()
    seed_places.seed()
    yield


routes = [
    Route("/", home),
    *auth_routes,
    *journal_routes,
    *places_routes,
    *inquiry_routes,
    *transit_routes,
    *admin_routes,
    Mount("/static", app=StaticFiles(directory=str(STATIC_DIR)), name="static"),
]

app = Starlette(debug=False, routes=routes, lifespan=lifespan)
