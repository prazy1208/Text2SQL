"""
FastAPI app entry point. All routes are mounted from backend.api.routes.
Serves the frontend at / (static files from frontend/).
Run from project root: uvicorn backend.api.main:app --reload

To add more agents: create api/routes/<name>.py with an APIRouter, then include_router in this file.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import query as query_routes
from backend.config import PROJECT_ROOT

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

# Frontend: serve static files at / (index.html, styles.css, app.js)
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
