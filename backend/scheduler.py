"""Background scheduler for periodic content refresh."""

import asyncio
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config import DEFAULT_INTERVAL, SOURCE_INTERVALS, logger
from backend.database import get_all_sources, update_source, upsert_content_items
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

        # Clear any earlier failure. The broadcast below already told the page
        # this source was healthy again, but the database was never updated to
        # match, so the red status dot survived every later success and the
        # source stayed marked as broken for good.
        #
        # last_fetched is stamped here rather than only when items arrive. It
        # was written inside the item upsert, which does not run for a feed
        # that returned nothing, so a source that fetched cleanly and had no
        # items looked like one that had never been fetched at all, and the
        # panel showed "Loading..." for as long as you cared to watch it.
        await update_source(
            source_id,
            status="active",
            last_error=None,
            last_fetched=datetime.utcnow().isoformat(),
        )
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
    """Schedule refresh jobs for every source that is not paused.

    Sources currently in error are included on purpose. Fetches fail for
    ordinary, temporary reasons: a feed goes down for an hour, a network drops,
    a host rate limits. Scheduling only status="active" meant a single failure
    took the source out of the rotation at the next restart and nothing could
    ever put it back, because the only thing that clears an error is a
    successful refresh and that refresh was no longer scheduled. Pausing stays
    the deliberate off switch.
    """
    sources = [s for s in await get_all_sources() if s["status"] != "paused"]
    for source in sources:
        schedule_source(
            source_id=source["id"],
            source_type=source["source_type"],
            url=source["url"],
            name=source["name"],
            interval_seconds=source["refresh_seconds"],
        )
    logger.info(f"Scheduled {len(sources)} sources")


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
