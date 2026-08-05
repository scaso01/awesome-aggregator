"""Every API call the frontend makes must hit a route the backend registers.

This exists because three separate frontend calls were aimed at endpoints that
do not exist, or at real endpoints with the wrong field names, and nothing
caught it. The backend tests passed, because the backend was fine. The frontend
built, because a wrong URL in a string literal is still a valid string. The
failures only appeared as a menu that quietly did nothing.

The check reads the JSX, pulls out every `fetch(`${API_BASE}/...`)` with its
method, and resolves it against the FastAPI route table.
"""

import re
from pathlib import Path

import pytest

from backend.app import app

FRONTEND_SRC = Path(__file__).parent.parent / "frontend" / "src"

# fetch(`${API_BASE}/some/path`  -- the opening of any API call
FETCH_PATTERN = re.compile(r"fetch\(\s*`\$\{API_BASE\}([^`]*)`", re.MULTILINE)
METHOD_PATTERN = re.compile(r"method:\s*['\"](\w+)['\"]")

# `${anything}` inside a path is a runtime value, and {param} is FastAPI's
# equivalent. Both collapse to the same placeholder so they can be compared.
JS_INTERPOLATION = re.compile(r"\$\{[^}]*\}")
FASTAPI_PARAM = re.compile(r"\{[^}]*\}")


def normalize(path: str) -> str:
    """Reduce a path to a comparable shape: no query string, params masked."""
    path = path.split("?")[0]
    path = JS_INTERPOLATION.sub(":x", path)
    path = FASTAPI_PARAM.sub(":x", path)
    return path.rstrip("/") or "/"


def backend_routes() -> set[tuple[str, str]]:
    """Every (method, normalized path) the app actually serves.

    Read from the OpenAPI schema rather than by walking `app.routes`. Walking
    the route objects is version fragile: under Starlette 1.x the routes added
    by `include_router` are not all flat attributes on `app.routes`, so this
    check saw six routes instead of the whole API and failed against every call
    the frontend makes. The schema is the documented public surface and is
    stable across both, which is exactly what a contract test should compare to.
    """
    routes = set()
    for path, operations in app.openapi()["paths"].items():
        for method in operations:
            if method.upper() in ("HEAD", "OPTIONS", "PARAMETERS"):
                continue
            routes.add((method.upper(), normalize(path)))
    return routes


def frontend_calls() -> list[tuple[str, str, str, int]]:
    """Every API call in the JSX as (method, path, file, line)."""
    calls = []
    for jsx in sorted(FRONTEND_SRC.rglob("*.jsx")):
        text = jsx.read_text(encoding="utf-8")
        for match in FETCH_PATTERN.finditer(text):
            raw_path = match.group(1)
            line = text[: match.start()].count("\n") + 1
            # The options object, if any, follows the URL. Look at the rest of
            # this call only, capped so the next call's method is not stolen.
            tail = text[match.end(): match.end() + 400]
            method_match = METHOD_PATTERN.search(tail.split("fetch(")[0])
            method = (method_match.group(1) if method_match else "GET").upper()
            calls.append((method, f"/api{raw_path}", jsx.name, line))
    return calls


def test_the_scan_actually_finds_calls():
    """A contract test that silently matches nothing would always pass."""
    calls = frontend_calls()
    assert len(calls) >= 25, f"only found {len(calls)} frontend API calls"
    paths = {c[1] for c in calls}
    assert "/api/sources/" in paths, "the sources call should always be found"


def test_the_route_table_is_populated():
    """Guards the guard.

    An empty or partial route table would fail every call below with a
    misleading "the backend does not serve this", which is exactly what
    happened when this read `app.routes` under a newer Starlette. The count
    check catches a table that quietly loses most of itself.
    """
    routes = backend_routes()
    assert len(routes) >= 25, (
        f"only {len(routes)} routes found, which is far short of the API. The "
        f"route table is being read wrongly, not the backend missing routes."
    )
    for expected in [
        ("GET", "/api/health"),
        ("POST", "/api/bookmarks"),
        ("POST", "/api/actions/hide"),
        ("PUT", "/api/views/reorder"),
        ("GET", "/api/digest/today"),
    ]:
        assert expected in routes, f"{expected} missing from the route table"


def resolves(method: str, path: str, routes: set[tuple[str, str]]) -> bool:
    """Does this call reach a route?

    An exact match is the common case. A literal segment can also legitimately
    fill a path parameter, which is how `/api/layouts/default` reaches
    `/api/layouts/{name}`, so compare segment by segment and let a `:x` on the
    route side absorb any single literal.
    """
    target = normalize(path)
    if (method, target) in routes:
        return True

    target_parts = target.split("/")
    for route_method, route_path in routes:
        if route_method != method:
            continue
        route_parts = route_path.split("/")
        if len(route_parts) != len(target_parts):
            continue
        if all(r == ":x" or r == t for r, t in zip(route_parts, target_parts)):
            return True
    return False


def test_a_literal_segment_can_fill_a_path_parameter():
    """Guards the matcher itself, so it cannot pass by being too permissive."""
    routes = {("GET", "/api/layouts/:x"), ("GET", "/api/health")}
    assert resolves("GET", "/api/layouts/default", routes)
    assert not resolves("GET", "/api/layouts/default/extra", routes)
    assert not resolves("POST", "/api/layouts/default", routes)
    assert not resolves("GET", "/api/nope", routes)


@pytest.mark.parametrize(
    "method,path,filename,line",
    frontend_calls(),
    ids=lambda v: str(v) if not isinstance(v, int) else f"L{v}",
)
def test_frontend_call_hits_a_real_route(method, path, filename, line):
    assert resolves(method, path, backend_routes()), (
        f"{filename}:{line} calls {method} {path}, which the backend does not "
        f"serve. Bookmarking was broken this exact way: the UI posted to "
        f"/api/actions/bookmark, which has never existed. Tab reordering was "
        f"broken the same way, POSTing to a route registered as PUT."
    )
