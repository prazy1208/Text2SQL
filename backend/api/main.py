"""
FastAPI app entry point. All routes are mounted from backend.api.routes.
Serves the frontend at / (static files from frontend/).
Run from project root: uvicorn backend.api.main:app --reload

To add more agents: create api/routes/<name>.py with an APIRouter, then include_router in this file.
"""

import logging
import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from backend.api.routes import query as query_routes
from backend.config import PROJECT_ROOT

mimetypes.init()
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    title="Text2SQL API",
    description="Text2SQL pipeline: Intent, Table/Column (FK-aware), Few-Shot, Gen-SQL, SQL validation.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes first (so /query, /use-cases take precedence)
app.include_router(query_routes.router)

# Frontend: serve static files from frontend/ and fall back to index.html.
# Using a catch-all route instead of StaticFiles mount at "/" avoids the mount
# intercepting API paths and guarantees correct MIME types on all platforms.
frontend_dir = PROJECT_ROOT / "frontend"
_frontend_resolved = frontend_dir.resolve()


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path:
        file_path = (frontend_dir / full_path).resolve()
        if file_path.is_file() and str(file_path).startswith(str(_frontend_resolved)):
            media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            return FileResponse(str(file_path), media_type=media_type)
    index = frontend_dir / "index.html"
    if index.is_file():
        return FileResponse(str(index), media_type="text/html")
    return Response("Not found", status_code=404)
