import pathlib
from starlette.templating import Jinja2Templates

TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


from .auth import is_admin  # noqa: E402

templates.env.globals["is_admin"] = is_admin
