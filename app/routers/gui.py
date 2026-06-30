import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["gui"])

_HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")


@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Serve the main dashboard SPA."""
    with open(_HTML_PATH, encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)
