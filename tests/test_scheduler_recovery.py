"""A source that fails a fetch has to be able to come back.

Found by running the app rather than reading it. Two panels sat red for hours
and never recovered, and the reason was a pair of gaps that only bite together:

  * `refresh_source` broadcast "active" to the page on a good fetch but never
    wrote that back to the database, so status stayed "error" for good.
  * `schedule_all_active_sources` scheduled `status = 'active'` rows only, so
    after the next restart the errored source was not scheduled at all.

The result is a feed that dies permanently the first time a network blip, a
rate limit, or an hour of downtime catches it. There is no retry button in the
UI, so the only cure was deleting the source and adding it back.
"""

import backend.scheduler as scheduler_module
from backend.database import create_source, get_source, update_source
from backend.scheduler import refresh_source, schedule_all_active_sources
from backend.sources.base import SourceFetchError


class FakeAdapter:
    """Stands in for a real source adapter.

    Returning no items is a perfectly ordinary successful fetch (a feed that
    has published nothing new), and it keeps this test off the content plumbing
    entirely. The path under test is what happens to the source's status.
    """

    def __init__(self, *args, **kwargs):
        pass

    async def fetch(self):
        return []


class FailingAdapter:
    def __init__(self, *args, **kwargs):
        pass

    async def fetch(self):
        raise SourceFetchError("host is unreachable")


async def test_a_failed_fetch_marks_the_source(db, monkeypatch):
    """The starting point: failures are recorded. This part always worked."""
    source = await create_source("Flaky", "rss", "https://example.com/a.xml")
    monkeypatch.setattr(scheduler_module, "create_source_adapter", FailingAdapter)

    await refresh_source(source["id"], "rss", source["url"], "Flaky")

    after = await get_source(source["id"])
    assert after["status"] == "error"
    assert "unreachable" in after["last_error"]


async def test_a_later_success_clears_the_error(db, monkeypatch):
    source = await create_source("Recovers", "rss", "https://example.com/b.xml")
    await update_source(source["id"], status="error", last_error="host is unreachable")

    monkeypatch.setattr(scheduler_module, "create_source_adapter", FakeAdapter)
    await refresh_source(source["id"], "rss", source["url"], "Recovers")

    after = await get_source(source["id"])
    assert after["status"] == "active", (
        "a successful refresh left the source marked broken, so its red dot "
        "never clears and it stays out of the schedule after a restart"
    )
    assert after["last_error"] is None


async def test_a_source_in_error_is_still_scheduled(db, monkeypatch):
    """The half that only shows up after a restart.

    Asserts on which sources get handed to the scheduler rather than on
    APScheduler's own state, because the decision is the thing that was wrong.
    """
    healthy = await create_source("Healthy", "rss", "https://example.com/c.xml")
    broken = await create_source("Broken", "rss", "https://example.com/d.xml")
    paused = await create_source("Paused", "rss", "https://example.com/e.xml")
    await update_source(broken["id"], status="error", last_error="429")
    await update_source(paused["id"], status="paused")

    scheduled = []
    monkeypatch.setattr(
        scheduler_module,
        "schedule_source",
        lambda source_id, **kwargs: scheduled.append(source_id),
    )

    await schedule_all_active_sources()

    assert healthy["id"] in scheduled
    assert broken["id"] in scheduled, (
        "an errored source was never rescheduled, so nothing could ever clear "
        "its error and the feed was retired permanently"
    )
    assert paused["id"] not in scheduled, "pausing is the deliberate off switch"
