"""Background scheduler for periodic content refresh."""

import asyncio
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config import DEFAULT_INTERVAL, SOURCE_INTERVALS, logger
from backend.database import get_active_sources, update_source, upsert_content_items
from backend.sources import create_source_adapter
from backend.sources.base import SourceFetchError
from backend.websocket import manager

scheduler = AsyncIOScheduler(timezone="UTC")
_refresh_tasks: dict[int, str] = {}  # source_id -> job_id


async def refresh_source(source_id: int, source_type: str, url: str, name: str):
    """Fetch new content from a single source and push updates."""
    try:
        adapter = create_source_adapter(source_type, url, name=name)
        items = await adapter.fetch()

        if items:
            item_dicts = [item.to_dict() for item in items]
            new_count = await upsert_content_items(source_id, item_dicts)

            if new_count > 0 and manager.client_count > 0:
                # Only push the latest items over WebSocket
                await manager.send_new_content(source_id, item_dicts[:10])

            logger.info(f"Refreshed '{name}': {len(items)} items ({new_count} new)")
        else:
            logger.debug(f"Refreshed '{name}': no items returned")

        await manager.send_source_update(source_id, "active")

    except SourceFetchError as e:
        error_msg = str(e)
        logger.warning(f"Source '{name}' fetch failed: {error_msg}")
        await update_source(source_id, status="error",
                            last_error=error_msg)
        await manager.send_source_update(source_id, "error", error=error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.error(f"Source '{name}' refresh failed: {error_msg}")
        await update_source(source_id, status="error",
                            last_error=error_msg)
        await manager.send_source_update(source_id, "error", error=error_msg)


def schedule_source(source_id: int, source_type: str, url: str,
                    name: str, interval_seconds: int = None):
    """Add or update a scheduled refresh job for a source."""
    if interval_seconds is None:
        interval_seconds = SOURCE_INTERVALS.get(source_type, DEFAULT_INTERVAL)

    job_id = f"refresh_source_{source_id}"

    # Remove existing job if any
    if source_id in _refresh_tasks:
        try:
            scheduler.remove_job(_refresh_tasks[source_id])
        except Exception:
            pass

    scheduler.add_job(
        refresh_source,
        "interval",
        seconds=interval_seconds,
        id=job_id,
        args=[source_id, source_type, url, name],
        replace_existing=True,
        next_run_time=datetime.utcnow() + timedelta(seconds=3),  # Brief delay for event loop readiness
    )
    _refresh_tasks[source_id] = job_id
    logger.info(f"Scheduled '{name}' (type={source_type}) every {interval_seconds}s")


def unschedule_source(source_id: int):
    """Remove a source's scheduled refresh job."""
    if source_id in _refresh_tasks:
        try:
            scheduler.remove_job(_refresh_tasks[source_id])
        except Exception:
            pass
        del _refresh_tasks[source_id]


async def schedule_all_active_sources():
    """Schedule refresh jobs for all active sources in the database."""
    sources = await get_active_sources()
    for source in sources:
        schedule_source(
            source_id=source["id"],
            source_type=source["source_type"],
            url=source["url"],
            name=source["name"],
            interval_seconds=source["refresh_seconds"],
        )
    logger.info(f"Scheduled {len(sources)} active sources")


def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
