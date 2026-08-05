"""FastAPI application entry point for Awesome Aggregator."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.config import SERVER_HOST, SERVER_PORT, DEBUG, DEFAULT_SOURCES, logger
from backend.database import get_db, close_db, create_source, get_all_sources, cleanup_expired_mutes
from backend.scheduler import (
    start_scheduler, stop_scheduler, schedule_all_active_sources, schedule_source,
    scheduler as background_scheduler,
)
from backend.websocket import manager
from backend.api.sources import router as sources_router
from backend.api.content import router as content_router
from backend.api.layouts import router as layouts_router
from backend.api.views import router as views_router
from backend.api.discover import router as discover_router
from backend.api.bookmarks import router as bookmarks_router
from backend.api.actions import router as actions_router
from backend.api.reader import router as reader_router
from backend.api.detect import router as detect_router
from backend.api.opml import router as opml_router
from backend.api.digest import router as digest_router
from backend.api.stats import router as stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting Awesome Aggregator...")

    # Initialize database
    await get_db()

    # Load default sources if database is empty
    existing = await get_all_sources()
    if not existing and DEFAULT_SOURCES:
        logger.info(f"Loading {len(DEFAULT_SOURCES)} default sources...")
        for src in DEFAULT_SOURCES:
            try:
                created = await create_source(
                    name=src["name"],
                    source_type=src["type"],
                    url=src["url"],
                    refresh_seconds=src.get("refresh_seconds", 300),
                )
                logger.info(f"  Added default source: {src['name']}")
            except Exception as e:
                logger.warning(f"  Failed to add default source '{src['name']}': {e}")

    # Start the background scheduler and schedule all active sources
    start_scheduler()
    await schedule_all_active_sources()

    # Schedule hourly cleanup of expired mutes
    if background_scheduler.running:
        background_scheduler.add_job(
            cleanup_expired_mutes,
            'interval',
            hours=1,
            id='cleanup_mutes',
            replace_existing=True,
        )

    logger.info("Awesome Aggregator is ready!")
    yield

    # Shutdown
    logger.info("Shutting down...")
    stop_scheduler()
    await close_db()


app = FastAPI(
    title="Awesome Aggregator",
    description="Customizable content dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(sources_router)
app.include_router(content_router)
app.include_router(layouts_router)
app.include_router(views_router)
app.include_router(discover_router)
app.include_router(bookmarks_router)
app.include_router(actions_router)
app.include_router(reader_router)
app.include_router(detect_router)
app.include_router(opml_router)
app.include_router(digest_router)
app.include_router(stats_router)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time content updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()
            # Client can send commands like {"action": "refresh", "source_id": 1}
            logger.debug(f"WebSocket message from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "websocket_clients": manager.client_count,
    }


# Serve the built frontend.
#
# This has to be the LAST thing registered. Starlette matches routes in
# registration order and a mount at "/" matches every path, so anything
# declared after it is unreachable. It used to sit above the WebSocket and
# health handlers, which meant that on any deployment where the frontend had
# been built, /ws and /api/health both returned 404 — and /ws being dead takes
# the real-time content push with it.
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=DEBUG,
    )
