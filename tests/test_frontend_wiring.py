"""Every frontend component must actually be rendered by something.

Two finished, styled, tested-behind components were imported nowhere and
rendered never: the reader overlay and the three dot action menu. Both are
headline features. Both looked complete in the source tree, both had CSS, and
neither could be reached by a user. A build does not fail over an unused
component, and no API test can see it.

This walks the component directory and checks each one is referenced as JSX by
another file.
"""

import re
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "frontend" / "src"
COMPONENTS = SRC / "components"


def component_names() -> list[str]:
    return sorted(p.stem for p in COMPONENTS.glob("*.jsx"))


def all_sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in SRC.rglob("*.jsx")}


def test_there_are_components_to_check():
    """Guard the guard: an empty scan would pass silently."""
    names = component_names()
    assert len(names) >= 8, f"only found {names}"
    assert "ContentPanel" in names


@pytest.mark.parametrize("name", component_names())
def test_component_is_imported_somewhere(name):
    sources = all_sources()
    importers = [
        f for f, text in sources.items()
        if f != f"{name}.jsx" and re.search(rf"\bimport\s+{name}\b", text)
    ]
    assert importers, (
        f"{name}.jsx is imported by nothing. It is dead code, and if it is a "
        f"feature the README advertises then that feature is unreachable. "
        f"ReaderMode and ItemActionMenu both shipped in exactly this state."
    )


@pytest.mark.parametrize("name", component_names())
def test_component_is_actually_rendered(name):
    """Importing is not enough. ReaderMode was imported and never rendered."""
    sources = all_sources()
    renderers = [
        f for f, text in sources.items()
        if f != f"{name}.jsx" and re.search(rf"<{name}[\s/>]", text)
    ]
    assert renderers, (
        f"{name} is never used as JSX. App.jsx imported ReaderMode and never "
        f"rendered it, so clicking an article opened a plain iframe instead of "
        f"the reader for the entire life of the project."
    )
