"""Точка входа FastAPI backend."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Добавляем backend в path для корректных импортов
sys.path.insert(0, str(Path(__file__).parent))

from api.routes import auth, dashboard, campaigns, conversations, leads, scraper, accounts, ws
from core.config import settings
from services.ws_manager import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    logger.info("Starting web backend...")
    logger.info(f"Outreach dir: {settings.outreach_dir}")
    logger.info(f"Cache dir: {settings.cache_dir}")

    # Запускаем file watcher для WebSocket
    await ws_manager.start_file_watcher(
        settings.outreach_dir,
        interval=settings.ws_check_interval_seconds,
    )
    logger.info("File watcher started")

    yield

    ws_manager.stop_file_watcher()
    logger.info("Web backend stopped")


app = FastAPI(
    title="LeadPhoneFinder Web API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(campaigns.router)
app.include_router(conversations.router)
app.include_router(leads.router)
app.include_router(scraper.router)
app.include_router(accounts.router)
app.include_router(ws.router)


@app.get("/api/health")
async def health() -> dict:
    """Health check."""
    return {
        "status": "ok",
        "outreach_dir_exists": settings.outreach_dir.exists(),
        "cache_dir_exists": settings.cache_dir.exists(),
        "ws_connections": len(ws_manager.active_connections),
    }
