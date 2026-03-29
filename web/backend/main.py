"""Точка входа FastAPI backend."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Добавляем backend в path для корректных импортов
backend_dir = str(Path(__file__).parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Добавляем project root для импорта bot.* пакетов
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.routes import auth, dashboard, campaigns, conversations, leads, scraper, accounts, ws
from core.config import settings
from core.deps import get_outreach_manager
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
    logger.info(f"Project root: {project_root}")
    logger.info(f"Outreach dir: {settings.outreach_dir}")
    logger.info(f"Cache dir: {settings.cache_dir}")
    logger.info(f"DB path: {settings.db_path}")

    # Создаём таблицы БД если не существуют
    from db.engine import create_tables
    create_tables(settings.db_path)

    # Запускаем file watcher для WebSocket (DB callback подключится позже)
    await ws_manager.start_file_watcher(
        settings.outreach_dir,
        interval=settings.ws_check_interval_seconds,
    )
    logger.info("File watcher started")

    # Запускаем OutreachManager в фоне — не блокирует startup
    import asyncio
    outreach_mgr = get_outreach_manager()

    async def _start_outreach():
        try:
            await outreach_mgr.startup()
            logger.info("OutreachManager started successfully")
        except Exception as e:
            logger.error(f"OutreachManager startup failed: {e}")
            logger.info("Web backend works in read-only mode (no outreach)")

    asyncio.create_task(_start_outreach())

    yield

    # Shutdown
    try:
        await outreach_mgr.shutdown()
    except Exception as e:
        logger.error(f"OutreachManager shutdown error: {e}")

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
