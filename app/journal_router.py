from starlette.responses import RedirectResponse
from starlette.routing import Route


async def journal_redirect(request):
    # The full journal was originally a single self-contained ~70MB HTML file
    # (base64-embedded photos/videos). Rather than re-engineering that whole
    # photo pipeline into DB rows right now, it's served as-is as a static
    # page so nothing already built is lost; it can be migrated to real rows
    # (Photo/Day tables) in a later pass if you want per-photo editing in the
    # admin UI.
    return RedirectResponse(url="/static/journal/index.html")


routes = [
    Route("/journal", journal_redirect),
]
