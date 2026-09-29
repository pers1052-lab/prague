import os
import pathlib
from starlette.templating import Jinja2Templates

TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Google Maps embed key: set GOOGLE_MAPS_KEY in .env (never commit the key itself)
templates.env.globals["maps_key"] = os.environ.get("GOOGLE_MAPS_KEY", "")
