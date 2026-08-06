"""Serve the test fixtures, with the sample feed's dates always current.

The sample feed used to carry fixed pubDates. It was written on one day and
every test that depends on recent content passed, then the clock rolled over
and the digest, which ranks the last 24 hours, had nothing to rank. Two tests
began skipping in CI overnight for no reason anybody changed. A fixture that
expires is worse than no fixture, because it fails long after the change that
"caused" it.

Dates are rewritten as the file is served, so the file on disk stays readable
and diffable and the feed is always fresh.

    python tests/fixtures/serve.py 8765
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent
PUBDATE = re.compile(rb"<pubDate>[^<]*</pubDate>")
# Spread the items over the last few hours, newest first, so ordering and
# "how long ago" rendering have something real to work with.
OFFSETS_MINUTES = (25, 70, 140, 260, 400, 520)


def freshen(xml: bytes) -> bytes:
    """Rewrite every pubDate to a recent time, keeping the original order."""
    now = datetime.now(timezone.utc)
    stamps = [
        f"<pubDate>{format_datetime(now - timedelta(minutes=m))}</pubDate>".encode()
        for m in OFFSETS_MINUTES
    ]
    count = 0

    def swap(_match: re.Match) -> bytes:
        nonlocal count
        stamp = stamps[min(count, len(stamps) - 1)]
        count += 1
        return stamp

    return PUBDATE.sub(swap, xml)


class FreshFeedHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802  (name fixed by the base class)
        name = self.path.split("?")[0].lstrip("/")
        target = FIXTURES / name
        if name.endswith(".xml") and target.is_file() and b"<pubDate>" in target.read_bytes():
            body = freshen(target.read_bytes())
            self.send_response(200)
            self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = partial(FreshFeedHandler, directory=str(FIXTURES))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"serving {FIXTURES} on port {port}, feed dates kept current")
        sys.stdout.flush()
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
