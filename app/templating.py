import functools
import hashlib
import pathlib
from starlette.templating import Jinja2Templates

TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


from .auth import is_admin  # noqa: E402

templates.env.globals["is_admin"] = is_admin


STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"


@functools.lru_cache(maxsize=None)
def asset(path: str) -> str:
    """/static URL with a content hash, so browsers fetch the new file after each deploy."""
    try:
        digest = hashlib.md5((STATIC_DIR / path).read_bytes()).hexdigest()[:10]
    except OSError:
        return f"/static/{path}"
    return f"/static/{path}?v={digest}"


templates.env.globals["asset"] = asset
