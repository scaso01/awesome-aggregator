# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2026-08-05

First public release. Everything below was found by running the app and clicking
through it, not by reading the source. Every one of these failed silently: the
backend was healthy, its tests passed, and the frontend compiled.

### Fixed, features that did not work at all

- **The three dot action menu was never on screen.** `ItemActionMenu` was a
  finished, styled component that nothing imported, so bookmarking, hiding and
  muting an item had no entry point in the interface. Its trigger is now
  attached to every item in every display format. Its CSS also positioned the
  trigger absolutely inside `.content-item`, which was not itself positioned,
  so it would have escaped its container even once rendered.
- **Reader mode was unreachable, twice over.** `ReaderMode` was imported into
  `App.jsx` and never rendered, so clicking an article opened a plainer iframe
  viewer instead. Once rendered, it still fell through to its own iframe
  fallback every single time, because it branched on a `content` field while the
  reader endpoint returns `content_html`. The extracted article view, the hero
  of the feature, had never been displayed. Its hero image and read time fields
  were read under the wrong names too.
- **The muted sources manager was unreachable.** `MutedSources` was orphaned in
  the same way. There is now a Muted button in the header, so a source muted for
  a month can be brought back before the month is up.
- **URL auto-detection had no entry point.** `SourcePreview` was orphaned as
  well, so the advertised "paste any URL to auto-detect with a preview" had no
  button behind it. Add Source, Custom URL now has a Preview action.
- **Bookmarking silently did nothing.** Both callers posted to
  `/api/actions/bookmark`, a route that has never existed, and the failure went
  into a bare catch. They now post to `/api/bookmarks/`.
- **The Bookmarks tab never loaded anything.** Its fetch only ran for numeric
  view ids, so the tab either sat on "No bookmarks yet" forever or showed
  whichever custom view was open last, presenting those items as bookmarks.
  Bookmarks can also now be removed from that tab, which was not possible from
  anywhere.
- **Hiding an item silently did nothing.** The request sent `item_id` where the
  API requires `content_item_id`, so every attempt was a 422.
- **Reordering view tabs silently did nothing.** The request was a POST carrying
  `{order: [...]}` against a route registered as PUT expecting `{view_ids: [...]}`,
  so it was wrong twice and could not have worked either way.
- **Every Reddit source was broken.** Reddit answers 403 on
  `www.reddit.com/r/<sub>/hot.json` for any client that is not signed in, and
  redirects `old.reddit.com` to a login page. Reddit sources now read the
  subreddit's public Atom feed. That feed carries no vote or comment counts, so
  Reddit items no longer show a score and the digest ranks them on recency. The
  default Reddit refresh interval moved from 2 minutes to 10, on both the source
  and the per-type setting, to stay inside Reddit's per-IP rate limit.
- **Every daily digest row rendered as "Untitled" with no link.** The endpoint
  returns `{rank, content_item, score}` and the view read the title and url off
  the wrapper.
- **The reading stats bar was pinned at zero.** It read `articles_today`,
  `articles_week` and a scalar `top_source`; the endpoint returns `today_count`,
  `week_count` and a `top_sources` list.
- **The dashboard layout reset on every reload.** Dragging and resizing was
  saved to the server on every change and never read back, so the board was
  recomputed from scratch each time the page loaded.
- **Bookmarking the same item twice returned a 500.** `content_item_id` is
  unique and the insert did not handle the conflict, so an ordinary repeat
  action raised an unhandled `IntegrityError`. It is idempotent now.
- **A YouTube channel could not be added by its handle.** The adapter only
  understood `/channel/UC...`, so a `@handle` address left the feed URL pointing
  at the channel's web page and the fetch died with "not well-formed (invalid
  token)". Handles are how channels are shared now. The channel id is resolved
  from the page on first fetch, and a URL that cannot be resolved gets a message
  naming the shapes that work. The detection pattern also missed
  `youtube.com/user/name` entirely and matched `youtube.com/channel/...` only by
  accident, through a bare `c` alternative swallowing `hannel`.
- **Pasting a feed address detected it as a plain web page.** Auto-detection
  looked for a feed linked from an HTML page, or at guessable paths beside it,
  but never checked whether the URL it was given was already a feed. Copying a
  feed address out of another reader is the ordinary case, and
  `https://hnrss.org/frontpage` came back as "generic" with no preview.
- **Reader mode showed a large "Untitled" heading.** Extraction returns the
  literal string `Untitled` when it finds no heading, and that is truthy, so it
  beat the perfectly good title already on the item.
- **OPML import and export could not be reached from the page.** Both endpoints
  worked and both had passing tests, and the README advertised the feature, but
  no control in the interface called either one. There are now Import and Export
  buttons in the header. Export is a plain link, so the endpoint's existing
  `Content-Disposition` header does the download with no JavaScript involved.
- **Adding a feed you already follow was a 500, and the dialog said nothing.**
  The `url` column is unique and the single add endpoint let the resulting
  `IntegrityError` out of the database layer, so an ordinary accidental repeat
  crashed with a stack trace in the log. The batch endpoint beside it has
  always skipped duplicates, so the two disagreed about what a duplicate is.
  It answers 409 with a readable reason now. The interface had the matching
  half of the problem: `addSource` acted only on success, so any refusal left
  the dialog open and unchanged with nothing on screen, which is
  indistinguishable from the click not registering. The reason is now shown in
  the dialog.
- **One failed fetch retired a source permanently.** A failure sets the source's
  status to `error`, and only sources with status `active` were scheduled at
  startup, so after the next restart that source was never fetched again. Its
  error could not clear either, because the only thing that clears one is a
  successful fetch. A feed that was briefly unreachable, or a subreddit that hit
  a rate limit once, was dead for good with no retry anywhere in the interface.
  Everything except a paused source is now scheduled, and a successful fetch
  clears the error state instead of only announcing it over the WebSocket.

### Fixed, other

- **The app could not start.** `python-multipart` was missing from
  `requirements.txt`. FastAPI refuses to register a route that takes an
  `UploadFile`, which the OPML import endpoint does, so `import backend.app`
  raised and nothing came up at all.
- **The real-time push was dead on any build with a frontend.** The `StaticFiles`
  mount at `/` was registered before `/ws` and `/api/health`. Starlette matches
  routes in registration order and a mount at `/` matches every path, so both
  returned 404 as soon as `frontend/dist` existed. The mount is now last.
- **OPML export returned a 500.** `ElementTree.write` was called with
  `encoding="unicode"` against a `BytesIO`.
- **The documented quick start pointed at the wrong port.** The README and setup
  guide said port 8000 while `config.yaml` and the Vite dev proxy both use 8001,
  so following the instructions gave a frontend that could not reach its API.
- **RSS descriptions reached the screen still encoded.** The adapter stripped
  HTML tags without decoding character references, so a summary rendered on the
  board as `written.&#160;It&#8217;s&#160;a trend`. The Reddit adapter had
  decoded all along, so this was one adapter out of step rather than a decision.

### Added

- `AGGREGATOR_CONFIG` selects a configuration file other than `config.yaml`,
  which is how CI runs against local fixture feeds and how you would run two
  instances from one checkout.

### Changed, testing

The recurring theme above is a whole tier of behaviour that no test could see.
These are the checks that would have caught each class.

- **The service is started before the suite runs, in CI as well.** The dashboard
  tests drive a live service over HTTP and skip themselves when nothing is
  listening. Without a service they simply vanished and the build still went
  green.
- **`tests/audit_skips.py` sorts skips into infrastructure and data.** An
  infrastructure skip fails the build, because it means coverage disappeared. A
  data-dependent skip is allowed, capped, and always printed, so the count
  cannot creep up unnoticed.
- **`tests/test_frontend_api_contract.py` resolves every `fetch` in the JSX
  against the real route table.** Bookmarking and tab reordering both aimed at
  routes that did not exist in the method they used.
- **`tests/test_frontend_wiring.py` asserts every component is imported and
  rendered.** Three finished components were connected to nothing.
- **`tests/test_ui_actions.py` replays each user action with the exact payload
  the interface sends.** Field name mismatches returned 422 into a bare catch.
- **`tests/test_browser.py` drives the real page in Chromium.** The orphaned
  components, the reader falling through to its iframe, the untitled digest rows
  and the resetting layout were invisible to everything else.
- **`tests/test_reddit_source.py` parses a real captured subreddit feed**, kept
  at `tests/fixtures/reddit_technology.atom.xml`. Hand written XML that happened
  to match the parser would have proved nothing.
- CI runs against fixture feeds served from localhost rather than the live
  internet, so the badge reflects this project rather than whether Reddit felt
  like answering a datacenter address.
- CI builds the frontend and asserts the built entry point references the bundle.
  A stale `frontend/public/index.html` used to shadow it, which produces a blank
  page in production and looks fine until it is served.
- **Every display format is opened and checked.** Six are offered and only the
  default one had ever been exercised. The action menu is grafted onto whatever
  a format branch returns, which works on a plain element and silently does
  nothing on anything else, so five formats were one refactor from losing their
  menu with nothing to notice. The gallery format genuinely has no menu, and
  that exclusion is now pinned by its own test so it cannot quietly spread.
- **A new item is proved to reach an open page.** CI already checked that `/ws`
  completes a handshake, which says nothing about whether anything is ever sent.
  A test now serves a feed it can rewrite, adds a story to it, and waits for that
  headline to appear in a browser that never reloads.
- **View keyword filters are exercised through the tab bar**, not only against
  the endpoint that applies them.
- **Nothing on the board may show an undecoded HTML entity.** One check across
  the rendered page covers every adapter and every format, which is the right
  altitude for a bug whose real shape is "encoded text reached a human".
- README rewritten for someone who has never seen the project. `SETUP.md` folded
  into it, since the two had already drifted apart.

## [0.2.0] - 2026-02-17

### Added

#### Phase 1: Views System + Tab Bar Navigation
- Full views CRUD (create, read, update, delete, reorder) with keyword filters
- Tab bar navigation: All, Bookmarks, Digest built-in tabs + custom view tabs
- View editor modal with name, emoji icon picker, source multi-select, keyword include/exclude chips
- Drag-to-reorder tabs via HTML5 DnD
- Content endpoint filtered by view's source_ids + keyword matching
- Extracted 4 components from App.jsx (ContentPanel, ArticleViewer, OnboardingPicker, AddSourceModal)

#### Phase 2: Content Card Actions (Bookmark, Hide, Mute)
- Bookmarks API (create, list, delete) with dedicated Bookmarks tab
- Three-dot action menu on content items: Bookmark, Hide, Mute (24h/1w/1m/permanent), Open in new tab
- Hidden items excluded from all content queries
- Muted sources excluded from feeds with optional expiry and auto-cleanup scheduler job
- Database tables: bookmarks, hidden_items, muted_sources

#### Phase 3: Reader Mode + URL Auto-Detection
- Full-screen reader mode with clean serif typography (680px max-width, 1.8 line-height)
- Article extraction via trafilatura (title, author, date, hero image, content HTML, word count, read time)
- Font size controls (A-/A+), loading skeleton, iframe fallback
- URL auto-detection: paste any URL to auto-detect YouTube/Reddit/RSS/generic source type
- Source preview with 3 sample items before subscribing

#### Phase 4: OPML + Clickbait Cleanup + Daily Digest
- OPML import/export (grouped by category, uses xml.etree.ElementTree)
- Clickbait headline cleanup: strips ALL CAPS, excessive punctuation, clickbait prefixes (BREAKING:, WATCH:, etc.), trailing site names
- Daily digest: top 10 items from last 24h scored by engagement + recency with diversity penalty

#### Phase 5: Source Preview + Reading Stats + Polish
- Reading event tracking (click, read, bookmark events)
- Reading stats summary (articles today/week, top sources, category breakdown)
- Stats bar displayed below tab bar
- Muted sources manager with expiry display and unmute controls

### Changed
- Refactored App.jsx from 977 lines to 459 lines (extracted 12 components)
- Extended CSS from 1261 to 1801 lines for all new components
- Database auto-migrates new columns on startup (sort_order, topic_filters, exclude_keywords, icon on views)
- app.py registers 10 API routers (was 4) + hourly mute cleanup job

### Tests
- New suites covering views, bookmarks, actions, headline cleanup, reader
  extraction, URL detection, OPML, digest scoring and reading stats

## [0.1.0] - 2026-02-12

### Added
- Initial project scaffolding
- CLAUDE.md, README.md, SETUP.md, REQUIREMENTS.md documentation
- Technology research document
- FastAPI backend skeleton with source adapter pattern
- React + Vite frontend skeleton with react-grid-layout
- RSS, YouTube, Reddit source adapters
- SQLite database layer
- APScheduler for background content refresh
- WebSocket support for real-time updates
- Dark theme support
- pytest test structure
