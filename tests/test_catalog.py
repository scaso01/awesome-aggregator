"""The shipped source catalog has to be sound, and its feeds have to be alive.

Twelve of the catalog's directly checkable feeds were dead when this was
written. Picking the Sports topic on a fresh install gave a new user three
panels that said "Loading..." forever, because ESPN answers this client with an
empty 202, and one 404. That is the first thing anyone who clones this ever
sees.

Two layers here, on purpose:

  * The structural checks run everywhere, including CI. They are pure data
    checks with no network, and they catch a bundle or a topic that points at a
    source that no longer exists.
  * The live check actually fetches every entry. It needs the internet, it is
    slow, and it depends on other people's servers being up, so CI does not run
    it. Run it by hand every so often:

        python -m pytest tests/test_catalog.py -m network -v
"""

import asyncio

import pytest

from backend.api.discover import (
    ONBOARDING_TOPICS,
    SOURCE_CATALOG,
    STARTER_BUNDLES,
)
from backend.sources import create_source_adapter
from backend.sources.base import SourceFetchError

CATALOG_NAMES = {s["name"] for s in SOURCE_CATALOG}


# --- Structure, no network ----------------------------------------------------


def test_the_catalog_is_not_empty():
    """Guards every check below, which would all pass on an empty list."""
    assert len(SOURCE_CATALOG) > 50


@pytest.mark.parametrize("entry", SOURCE_CATALOG, ids=lambda e: e["name"])
def test_every_entry_is_complete(entry):
    for field in ("name", "category", "type", "url", "description"):
        assert entry.get(field), f"{entry.get('name')} is missing {field}"
    assert entry["type"] in ("rss", "youtube", "reddit", "generic")
    assert entry["url"].startswith("http"), entry["url"]


def test_no_duplicate_names():
    names = [s["name"] for s in SOURCE_CATALOG]
    dupes = {n for n in names if names.count(n) > 1}
    assert not dupes, f"the picker would show these twice: {dupes}"


def test_no_duplicate_urls():
    urls = [s["url"] for s in SOURCE_CATALOG]
    dupes = {u for u in urls if urls.count(u) > 1}
    assert not dupes, f"same feed under two names: {dupes}"


@pytest.mark.parametrize("bundle", STARTER_BUNDLES, ids=lambda b: b["name"])
def test_every_bundle_points_at_real_sources(bundle):
    """A bundle naming a source that was removed adds nothing and says nothing.

    The Sports bundle listed three ESPN feeds and Bleacher Report, all dead.
    """
    missing = [n for n in bundle["source_names"] if n not in CATALOG_NAMES]
    assert not missing, f"{bundle['name']} names sources that do not exist: {missing}"
    assert bundle["source_names"], f"{bundle['name']} is empty"


@pytest.mark.parametrize("topic", ONBOARDING_TOPICS, ids=lambda t: t["name"])
def test_every_onboarding_topic_has_sources(topic):
    """The first-run picker offers these. An empty one is a dead end."""
    categories = set(topic.get("categories", []))
    matched = [s for s in SOURCE_CATALOG if s["category"] in categories]
    assert matched, f"the {topic['name']} topic would add nothing"


# --- The feeds are actually alive, network required ---------------------------


def fetch_catalog_entry(entry):
    """Fetch one entry through the app's own adapter.

    Going through the adapter rather than a plain HTTP check is deliberate: a
    feed counts as working only if this app can turn it into items. ESPN
    answered 202 to a plain request and looked fine.
    """
    async def run():
        adapter = create_source_adapter(entry["type"], entry["url"], name=entry["name"])
        return await asyncio.wait_for(adapter.fetch(), timeout=45)

    return asyncio.run(run())


@pytest.mark.network
@pytest.mark.parametrize(
    "entry",
    [
        s for s in SOURCE_CATALOG
        # Reddit rate limits per IP hard enough that running these back to back
        # guarantees a 429, which says nothing about the catalog. RSSHub entries
        # only work for someone running RSSHub, which is documented as optional.
        if s["type"] != "reddit" and "://localhost" not in s["url"]
    ],
    ids=lambda e: e["name"],
)
def test_catalog_entry_is_alive(entry):
    try:
        items = fetch_catalog_entry(entry)
    except SourceFetchError as exc:
        pytest.fail(f"{entry['name']} ({entry['url']}) is dead: {exc}")
    except asyncio.TimeoutError:
        pytest.fail(f"{entry['name']} ({entry['url']}) did not answer in 45s")

    assert items, (
        f"{entry['name']} ({entry['url']}) fetched with no error and no items. "
        f"That is how the ESPN feeds looked while three panels sat on "
        f"\"Loading...\" forever."
    )


# --- Only offer what this installation can actually use ------------------------


async def test_rsshub_sources_are_not_offered_when_rsshub_is_down(client):
    """Sixteen catalog entries are RSSHub routes.

    RSSHub is a separate service this project does not ship and the README
    calls optional, so for anyone who has not run one these were sixteen
    entries in the picker that could only ever produce a connection error.
    Adding a source that cannot work is worse than not offering it.
    """
    import backend.api.discover as discover

    discover._RSSHUB_STATE = (None, False)  # no cached answer from another test

    for path in ("/api/discover/suggestions", "/api/discover/onboarding/sources?topics=news"):
        res = await client.get(path)
        assert res.status_code == 200, res.text
        offered = res.json()
        rsshub = [s for s in offered if s["url"].startswith(discover.RSSHUB_URL)]
        assert not rsshub, (
            f"{path} offered {len(rsshub)} source(s) that need RSSHub, which is "
            f"not running: {[s['name'] for s in rsshub][:3]}"
        )


async def test_the_rsshub_entries_are_filtered_not_deleted(client):
    """They come back for anyone who does run RSSHub, so the catalog keeps them."""
    from backend.api.discover import SOURCE_CATALOG, is_rsshub_source

    kept = [s for s in SOURCE_CATALOG if is_rsshub_source(s)]
    assert kept, "the RSSHub entries were removed rather than filtered"


async def test_topic_counts_match_what_gets_added(client):
    """The card says "14 sources". It has to mean it.

    Counting the whole catalog while the add path filtered would promise more
    than the picker delivers.
    """
    import backend.api.discover as discover

    discover._RSSHUB_STATE = (None, False)

    topics = (await client.get("/api/discover/onboarding/topics")).json()
    assert topics
    for topic in topics:
        added = (
            await client.get(f"/api/discover/onboarding/sources?topics={topic['id']}")
        ).json()
        assert len(added) == topic["source_count"], (
            f"the {topic['name']} card promises {topic['source_count']} sources "
            f"and adds {len(added)}"
        )
