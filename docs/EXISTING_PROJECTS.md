# Existing Open-Source Projects Research

> Last updated: 2026-02-12
> Purpose: Evaluate existing OSS projects relevant to the awesome-aggregator vision --
> a Flipboard-like customizable content dashboard with drag-and-drop grid layout,
> aggregating ANY web content (YouTube, Reddit, email, LinkedIn, Instagram, Facebook, news, etc.)

---

## Table of Contents

1. [Dashboard Launchers / Homepages](#1-dashboard-launchers--homepages)
2. [RSS Feed Readers](#2-rss-feed-readers)
3. [Content Aggregators and Flipboard Alternatives](#3-content-aggregators-and-flipboard-alternatives)
4. [RSS Generation (RSS-Bridge, RSSHub)](#4-rss-generation-rss-bridge-rsshub)
5. [System Monitoring Dashboards](#5-system-monitoring-dashboards)
6. [Drag-and-Drop Grid Libraries](#6-drag-and-drop-grid-libraries)
7. [Social Media Aggregators](#7-social-media-aggregators)
8. [Key Takeaways and What We Can Reuse](#8-key-takeaways-and-what-we-can-reuse)
9. [Gap Analysis: What None of These Do](#9-gap-analysis-what-none-of-these-do)

---

## 1. Dashboard Launchers / Homepages

These projects create a start page for self-hosted services. They are link launchers with
optional widgets -- NOT content aggregators. They show icons/links to apps, not the content itself.

### Homepage (gethomepage/homepage)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/gethomepage/homepage |
| **Stars** | 28,400 |
| **Last Update** | Feb 2026 (v1.10.1) -- very active |
| **License** | GPL-3.0 |
| **Tech Stack** | Next.js, React, Tailwind CSS, pnpm, Vitest |
| **What It Does** | Statically generated application dashboard with 100+ service integrations. API requests are proxied for security. Docker label-based auto-discovery. 40+ languages. |

**What We Can Learn:**
- Service integration pattern (100+ integrations via proxied API calls) is excellent architecture
- Docker label discovery pattern for auto-configuring widgets
- Next.js + Tailwind is a proven stack for dashboards
- Their widget system is well-designed but YAML-configured, not drag-and-drop

**How It Differs:** Pure link launcher with status widgets. No content display, no RSS, no drag-and-drop grid, no user-generated layouts. Configuration is YAML files, not a GUI.

---

### Dashy (lissy93/dashy)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/lissy93/dashy |
| **Stars** | 24,000 |
| **Last Update** | Dec 2024 |
| **License** | MIT |
| **Tech Stack** | Vue.js, Node.js, Yarn |
| **What It Does** | Self-hostable personal dashboard with status monitoring, widgets, themes, icon packs, and a UI config editor. Multi-page, multi-language, PWA-capable. |

**What We Can Learn:**
- UI-based config editor (no YAML editing required) -- important UX pattern
- Widget system with dynamic content
- Cloud backup/restore feature
- Theme system with 15+ built-in themes
- PWA for offline access

**How It Differs:** Still primarily a link launcher. Widgets show status data, not content feeds. No drag-and-drop grid repositioning. No RSS/content aggregation.

---

### Homer (bastienwirtz/homer)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/bastienwirtz/homer |
| **Stars** | 11,100 |
| **Last Update** | Nov 2025 (v25.11.1) |
| **License** | Apache-2.0 |
| **Tech Stack** | Vue.js, SCSS, PWA |
| **What It Does** | Dead-simple static homepage from a YAML config. Lightweight, fast, low maintenance. Fuzzy search, multi-page, keyboard shortcuts. |

**What We Can Learn:**
- Extreme simplicity works -- 11K stars for a YAML-to-page renderer
- Smart cards can pull data from service APIs (weather, etc.)
- PWA installability is valued by users

**How It Differs:** Static page generator. No interactivity, no drag-and-drop, no content feeds. Pure link organization.

---

### Heimdall (linuxserver/Heimdall)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/linuxserver/Heimdall |
| **Stars** | 9,000 |
| **Last Update** | Jan 2025 |
| **License** | MIT |
| **Tech Stack** | Laravel 10 (PHP 8.1+), SQLite, jQuery |
| **What It Does** | Application dashboard with tile-based launcher. Enhanced apps pull live stats (download speeds, queue sizes). 22+ languages. |

**What We Can Learn:**
- Enhanced apps concept: tiles that show live data from service APIs
- Automatic icon and color assignment from app metadata
- Multi-arch Docker images (x86, ARM)

**How It Differs:** Tile launcher only. No content display, no RSS, no grid customization. Older tech stack (jQuery, Laravel).

---

### Flame (pawelmalak/flame)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/pawelmalak/flame |
| **Stars** | 6,200 |
| **Last Update** | ~2024 (304 commits total, slower development) |
| **License** | MIT |
| **Tech Stack** | React, Redux, TypeScript, Node.js/Express, SQLite |
| **What It Does** | Self-hosted startpage with GUI editors for apps/bookmarks. Weather widget, Docker label integration, 15 color themes, search bar with 11 providers. |

**What We Can Learn:**
- GUI-first approach (no YAML/config files) -- key UX differentiator
- Built-in search with multiple provider support
- Weather widget pattern
- React + TypeScript + Express stack

**How It Differs:** Simple startpage. No content feeds, no grid layout, no drag-and-drop. Slower development pace.

---

### Homarr (homarr-labs/homarr)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/homarr-labs/homarr |
| **Stars** | 3,000+ |
| **Last Update** | Feb 2026 (v1.53.0) -- very active |
| **License** | Apache-2.0 |
| **Tech Stack** | TypeScript (91%), Next.js, tRPC, WebSockets, Redis, pnpm/Turbo monorepo |
| **What It Does** | Modern dashboard with drag-and-drop grid, 30+ integrations, 11K+ built-in icons, user management with permissions, OIDC/LDAP SSO, real-time updates. No YAML required. |

**What We Can Learn:**
- **CLOSEST to our vision in the dashboard launcher category**
- Drag-and-drop grid layout is implemented and working
- tRPC for type-safe API calls between frontend and backend
- WebSocket-based real-time updates
- Modern monorepo structure (pnpm + Turbo)
- User management with groups and permissions
- Kubernetes/Helm support

**How It Differs:** Still focused on service management/monitoring, not content consumption. Widgets show app status, not content feeds. But the drag-and-drop grid + modern stack is very relevant.

---

### Organizr (causefx/Organizr)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/causefx/Organizr |
| **Stars** | 5,700 |
| **Last Update** | Active (4,192 commits) |
| **License** | GPL-3.0 |
| **Tech Stack** | PHP 7.2+, JavaScript, Less/SCSS |
| **What It Does** | Tab-based HTPC dashboard. Loads services in iframes within tabs. Authentication via Plex/Emby/LDAP. User groups and permissions. Fail2ban integration. |

**What We Can Learn:**
- iframe-based content embedding -- simple way to show external content
- Tab-based navigation for organizing multiple content sources
- Multi-user auth with service-based login (Plex, Emby)
- URL routing (example.com/#ServiceName)

**How It Differs:** Uses iframes/tabs, not a grid layout. HTPC/media-server focused. Older PHP stack. No drag-and-drop, no content parsing.

---

## 2. RSS Feed Readers

These projects read and display RSS/Atom feeds. They handle feed parsing, storage, and presentation
but are designed as traditional reader UIs (list/card view), not customizable grid dashboards.

### FreshRSS (FreshRSS/FreshRSS)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/FreshRSS/FreshRSS |
| **Stars** | 14,000 |
| **Last Update** | Dec 2024 (active development) |
| **License** | AGPL-3.0 |
| **Tech Stack** | PHP 8.1+, PostgreSQL/SQLite/MySQL, JavaScript |
| **What It Does** | Full-featured RSS aggregator. Multi-user, custom tags, WebSub push, XPath web scraping, Google Reader + Fever API, CLI, extension system. Handles 1M+ articles and 50K+ feeds. |

**What We Can Learn:**
- **Best-in-class RSS engine** -- handles massive scale
- WebSub for real-time push updates (no polling needed)
- Built-in web scraping via XPath for sites without RSS
- Extension/plugin architecture for adding features
- Google Reader API compatibility means many mobile apps work out of the box
- Fever API support (de facto standard for RSS reader interop)

**How It Differs:** Traditional RSS reader UI (list view). No grid layout, no drag-and-drop, no non-RSS content sources. PHP stack.

---

### Miniflux (miniflux/v2)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/miniflux/v2 |
| **Stars** | 8,800 |
| **Last Update** | Jan 2026 (v2.2.16) -- active |
| **License** | Apache-2.0 |
| **Tech Stack** | Go (87%), PostgreSQL, minimal JS/CSS, single binary |
| **What It Does** | Minimalist, opinionated feed reader. Strips tracking pixels/UTM params. Full-text search via PostgreSQL. 25+ integrations (Discord, Slack, Telegram, Notion). Passkeys/WebAuthn auth. |

**What We Can Learn:**
- Single binary deployment in Go -- extremely simple ops
- Privacy-first: strips trackers, sanitizes content
- 25+ third-party integrations for content forwarding
- PostgreSQL full-text search is powerful and free
- Custom scraper rules for sites with truncated feeds

**How It Differs:** Deliberately minimal UI. No customization, no grid, no drag-and-drop. RSS-only.

---

### NewsBlur (samuelclay/NewsBlur)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/samuelclay/NewsBlur |
| **Stars** | 7,300 |
| **Last Update** | Active |
| **License** | MIT |
| **Tech Stack** | Python (Django), JavaScript, MongoDB, PostgreSQL, Redis, Elasticsearch |
| **What It Does** | Personal news reader with intelligence trainer -- users manually mark stories/authors/tags as liked/disliked. Social features (blurblogs). Original site view. YouTube channel support. Native iOS/Android apps. |

**What We Can Learn:**
- **Intelligence trainer** (manual ML) for content relevance -- unique feature
- Social layer (blurblogs) for sharing curated content
- Original site view renders content in context
- YouTube channel subscriptions (not just RSS)
- Full-text search across all subscriptions
- Story tagging system

**How It Differs:** Reader/list UI, not a grid dashboard. Complex stack (Django + MongoDB + PostgreSQL + Redis + Elasticsearch). Free tier limited to 64 sites.

---

### Tiny Tiny RSS (tt-rss/tt-rss)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/tt-rss/tt-rss |
| **Stars** | ~600 (new fork; original had 6K+ before retirement) |
| **Last Update** | Oct 2025 (community fork after original retired Nov 2025) |
| **License** | GPL-3.0 |
| **Tech Stack** | PHP, PostgreSQL |
| **What It Does** | Long-running RSS reader. Feed categorization, custom filters, article sharing, email digests, plugin system, API. |

**What We Can Learn:**
- Plugin/theme architecture survived 10+ years of development
- Custom filters and email digest features
- Cautionary tale: original maintainer burned out and shut down the project

**How It Differs:** Traditional RSS reader. Project went through leadership transition. Not recommended as foundation due to stability concerns.

---

### Yarr (nkanaev/yarr)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/nkanaev/yarr |
| **Stars** | 3,700 |
| **Last Update** | Nov 2025 (v2.6) |
| **License** | MIT |
| **Tech Stack** | Go (72%), SQLite, single binary |
| **What It Does** | Yet another RSS reader -- minimal RSS reader as a single binary. Desktop app with system tray OR self-hosted server. Fever API. Cross-platform. |

**What We Can Learn:**
- Single-binary-with-embedded-DB pattern (Go + SQLite) is excellent for distribution
- Can run as both desktop app and server from same binary
- System tray integration for desktop use

**How It Differs:** Extremely minimal. No multi-user, no plugins, no content beyond RSS.

---

### Stringer (stringer-rss/stringer)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/stringer-rss/stringer |
| **Stars** | 3,800 |
| **Last Update** | Moderate activity |
| **License** | MIT |
| **Tech Stack** | Ruby on Rails, PostgreSQL, Backbone.js, GoodJob |
| **What It Does** | Anti-social RSS reader (deliberately no sharing features). Fever API support. Heroku-deployable. |

**What We Can Learn:**
- Anti-social philosophy -- focus on personal consumption, not sharing
- Fever API as the standard for mobile app compatibility

**How It Differs:** Minimal feature set. Ruby stack. No grid, no customization, RSS-only.

---

### CommaFeed (Athou/commafeed)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/Athou/commafeed |
| **Stars** | 3,400 |
| **Last Update** | Feb 2026 (v6.2.0) -- very active |
| **License** | Apache-2.0 |
| **Tech Stack** | Java (Quarkus), React/TypeScript, H2/PostgreSQL/MySQL |
| **What It Does** | Google Reader-inspired RSS reader. Low memory footprint via native compilation. Multiple layout options, keyboard shortcuts, 25+ languages, Fever API, browser extension. |

**What We Can Learn:**
- Quarkus native compilation = fast startup + low memory
- React/TypeScript frontend is modern and maintainable
- Free public instance with no ads/tracking (funded by donations)

**How It Differs:** Traditional RSS reader UI. No grid, no drag-and-drop, no non-RSS content.

---

### Feedbin (feedbin/feedbin)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/feedbin/feedbin |
| **Stars** | 3,700 |
| **Last Update** | Active |
| **License** | MIT |
| **Tech Stack** | Ruby on Rails, PostgreSQL, Redis, Elasticsearch, Sidekiq |
| **What It Does** | RSS reader that also handles email newsletters. Full-content extraction for truncated feeds. Image proxy. Face detection for preview cropping. |

**What We Can Learn:**
- **Email newsletter ingestion** -- unique feature, very relevant to our vision
- Full-content extraction (pulls full articles from truncated RSS)
- Image proxy for privacy
- Face detection for intelligent image cropping

**How It Differs:** Complex infrastructure (Rails + PostgreSQL + Redis + Elasticsearch). Maintainers explicitly discourage self-hosting. Reader UI only, no grid/dashboard.

---

## 3. Content Aggregators and Flipboard Alternatives

### Glance (glanceapp/glance)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/glanceapp/glance |
| **Stars** | 31,900 |
| **Last Update** | Jun 2025 (v0.8.4) |
| **License** | AGPL-3.0 |
| **Tech Stack** | Go (56%), HTML, JavaScript, CSS, single binary <20MB |
| **What It Does** | Self-hosted dashboard that puts ALL feeds in one place. RSS, Reddit, Hacker News, YouTube, Twitch, weather, markets, Docker status, server stats. Custom widgets via iframe/HTML/API. YAML config, mobile-responsive, themeable. |

**What We Can Learn:**
- **CLOSEST project to our vision overall** -- aggregates diverse content types into one view
- Multi-source support: RSS, Reddit, HN, YouTube, Twitch, weather, markets
- Custom widget system via iframe, HTML, extensions, or API endpoints
- Single binary in Go, under 20MB -- incredible distribution story
- 31.9K stars shows massive demand for this type of tool
- Mobile-responsive design
- Lightweight: minimal JS, low memory usage

**How It Differs:**
- **No drag-and-drop** -- layout is YAML-configured, not interactive
- **No user accounts** -- single-user only
- No email, LinkedIn, Instagram, Facebook integration
- No content interaction (cannot like, save, or share within the app)
- Static layout -- users cannot rearrange widgets at runtime

**Gap:** If Glance had drag-and-drop and more content sources, it would BE our project. This is the number one competitor/inspiration.

---

### RSSbrew (yinan-c/RSSbrew)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/yinan-c/RSSbrew |
| **Stars** | 268 |
| **Last Update** | Sep 2025 (v2025.6) |
| **License** | AGPL-3.0 |
| **Tech Stack** | Python (93%), Docker |
| **What It Does** | RSS aggregation tool with AI summarization. Combines multiple feeds, applies regex filters, generates AI summaries via OpenAI-compatible APIs, creates daily/weekly digests. |

**What We Can Learn:**
- **AI-powered content summarization** -- cutting-edge feature for content aggregation
- Filter rules with regex + boolean logic (AND/OR/NOT)
- Digest compilation (daily/weekly) with AI summarization
- OpenAI-compatible API integration (works with any LLM provider)

**How It Differs:** RSS processing pipeline, not a dashboard. No UI for consumption -- it outputs processed RSS feeds. Small project, early stage.

---

## 4. RSS Generation (RSS-Bridge, RSSHub)

These are CRITICAL infrastructure for our project. They convert non-RSS sources into RSS feeds,
which we can then consume in our dashboard.

### RSSHub (DIYgod/RSSHub)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/DIYgod/RSSHub |
| **Stars** | 41,800 |
| **Last Update** | Active (5,000+ global instances) |
| **License** | AGPL-3.0 |
| **Tech Stack** | Node.js, Docker |
| **What It Does** | Everything is RSSible. Generates RSS feeds from 1,000+ sources including YouTube, Twitter/X, Reddit, Instagram, Spotify, GitHub, Telegram, and hundreds more. Browser extension (RSSHub Radar) auto-detects available feeds. |

**What We Can Learn:**
- **THE key infrastructure piece for our project**
- 1,000+ route definitions covering virtually every major platform
- Self-hostable to avoid rate limits
- RSSHub Radar browser extension detects available feeds on any page
- Massive community continuously adding new routes
- Can convert social media, e-commerce, forums, and more to RSS

**How It Differs:** Feed GENERATOR, not a reader or dashboard. Outputs RSS feeds that need to be consumed by another tool. No UI for reading content.

**Integration Plan:** Self-host RSSHub as our backend content source normalizer. Any content source our users want can potentially be converted to RSS via RSSHub routes.

---

### RSS-Bridge (RSS-Bridge/rss-bridge)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/RSS-Bridge/rss-bridge |
| **Stars** | 8,700 |
| **Last Update** | Oct 2024 |
| **License** | Unlicense (Public Domain) |
| **Tech Stack** | PHP 7.4+, no framework |
| **What It Does** | Generates RSS/Atom/JSON feeds for sites that lack them. 447+ bridges for platforms including Reddit, YouTube, TikTok, Twitch, Mastodon. CssSelectorBridge can scrape ANY site using CSS selectors. Caching to prevent bans. |

**What We Can Learn:**
- 447+ bridges is an enormous library of site-specific scrapers
- **CssSelectorBridge**: generic bridge that scrapes ANY website using CSS selectors -- incredibly powerful
- Public Domain license means we can use/modify anything freely
- Caching layer to prevent rate limiting/bans
- Multiple output formats (RSS, Atom, JSON, HTML)

**How It Differs:** PHP-based, separate from RSSHub. Smaller route library than RSSHub but includes the invaluable CssSelectorBridge for arbitrary sites. Slightly less active development.

**Integration Plan:** Use alongside RSSHub. RSS-Bridge CssSelectorBridge handles the long tail of sites that RSSHub does not cover.

---

## 5. System Monitoring Dashboards

### Grafana (grafana/grafana)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/grafana/grafana |
| **Stars** | 72,100 |
| **Last Update** | Continuously (65K+ commits) |
| **License** | AGPL-3.0 (with Apache-2.0 exceptions) |
| **Tech Stack** | TypeScript, Go, React |
| **What It Does** | The open-source observability platform. Drag-and-drop dashboard builder. Plugin system for data sources. Alerting, annotations, templating. |

**What We Can Learn:**
- **Gold standard for drag-and-drop dashboard UX** -- massive investment in grid/panel UX
- Plugin architecture for data source adapters
- Dashboard templating and variables
- Panel/widget system with resize handles
- Dashboard sharing and export

**How It Differs:** Designed for metrics/logs/traces, not content consumption. Overkill for our use case. Complex infrastructure requirements. But the dashboard UX patterns are the benchmark.

---

### Glances (nicolargo/glances)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/nicolargo/glances |
| **Stars** | 31,600 |
| **Last Update** | Dec 2024 |
| **License** | LGPL-3.0 |
| **Tech Stack** | Python, Web UI, REST API |
| **What It Does** | System monitoring (CPU, memory, disk, network, processes). Web UI, REST/XML-RPC API. Exports to InfluxDB, Prometheus, Elasticsearch, etc. |

**What We Can Learn:**
- REST API design for exposing system data as widgets
- Export to multiple backends pattern

**How It Differs:** System monitoring only. Not relevant to content aggregation except as a possible widget source.

---

## 6. Drag-and-Drop Grid Libraries

These are the building blocks for our dashboard layout engine.

### React-Grid-Layout

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/react-grid-layout/react-grid-layout |
| **Stars** | 22,100 |
| **License** | MIT |
| **Tech Stack** | React, TypeScript |
| **What It Does** | Draggable + resizable grid layout with responsive breakpoints. CSS transform positioning. Serializable layouts. No jQuery. |

**Key for Us:**
- **Primary candidate for our grid engine**
- 22K stars, mature, well-tested
- Responsive breakpoints with per-breakpoint layouts
- Layouts are serializable (can persist to DB)
- Vertical/horizontal compaction algorithms
- Min/max width/height constraints on widgets

---

### GridStack.js

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/gridstack/gridstack.js |
| **Stars** | 8,700 |
| **License** | MIT |
| **Tech Stack** | TypeScript, framework-agnostic (Angular, React, Vue, etc.) |
| **What It Does** | Mobile-friendly dashboard grid with drag-and-drop and resize. Native touch events. 1-12 column grid. Zero dependencies. |

**Key for Us:**
- Framework-agnostic -- works with React, Vue, Angular, or vanilla JS
- Native touch/mobile support built-in
- Zero external dependencies
- Collision detection and auto-positioning

---

### Muuri

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/haltu/muuri |
| **Stars** | ~11,000 |
| **License** | MIT |
| **What It Does** | Layout engine with sorting, filtering, and drag-and-drop (including between grids). Animations. Touch support. |

**Key for Us:**
- Drag between grids (useful for multi-page dashboards)
- Filtering and sorting built-in
- Smooth animations
- Custom layout functions (any positioning algorithm)

---

## 7. Social Media Aggregators

### Postiz (gitroomhq/postiz-app)

| Field | Value |
|-------|-------|
| **GitHub** | https://github.com/gitroomhq/postiz-app |
| **Stars** | Growing rapidly |
| **License** | Open source |
| **What It Does** | Social media scheduling tool. Supports X, Bluesky, Mastodon, Discord, Facebook, Instagram, TikTok, YouTube, Reddit, LinkedIn, Threads, Pinterest. |

**What We Can Learn:**
- OAuth integration patterns for 12+ social platforms
- Multi-platform API abstraction layer

**How It Differs:** Posting/scheduling tool, not a reader/aggregator. But the platform integration code is valuable reference.

---

### Mixpost

| Field | Value |
|-------|-------|
| **Website** | https://mixpost.app/ |
| **License** | Open source (self-hosted) |
| **What It Does** | Unified social media management across 11 platforms. |

**What We Can Learn:**
- Self-hosted social media management patterns
- Multi-platform OAuth and API patterns

**How It Differs:** Management/posting tool, not consumption/reading.

---

## 8. Key Takeaways and What We Can Reuse

### Architecture Inspiration

| Component | Best Reference Project | Why |
|-----------|----------------------|-----|
| **Grid Layout** | React-Grid-Layout | 22K stars, mature, serializable layouts, responsive breakpoints |
| **Content Normalization** | RSSHub + RSS-Bridge | Convert ANY source to RSS. 1,000+ routes + CSS selector scraping |
| **Feed Engine** | FreshRSS or Miniflux | Proven at scale (1M+ articles). WebSub, scraping, API compatibility |
| **Dashboard UX** | Homarr + Glance | Drag-and-drop grid (Homarr) + multi-source feeds (Glance) |
| **AI Summarization** | RSSbrew | OpenAI-compatible content summarization and digest generation |
| **Email Ingestion** | Feedbin | Newsletter-to-feed conversion |
| **Social APIs** | Postiz | OAuth patterns for 12+ social platforms |
| **Real-time Updates** | Homarr | WebSocket + tRPC pattern |

### Technology Stack Signals

Based on the most successful projects:
- **Frontend:** React/Next.js + TypeScript dominates (Homepage 28K stars, Dashy 24K, Homarr active)
- **Grid Library:** React-Grid-Layout (22K stars) or GridStack.js (8.7K) for drag-and-drop
- **Backend:** Go (Glance, Miniflux, Yarr) for performance or Node.js/Next.js for full-stack
- **Database:** PostgreSQL (most projects) or SQLite (simpler deployments)
- **Content Normalization:** RSSHub (41.8K stars) as the universal RSS generator
- **Deployment:** Docker-first with single-binary option as stretch goal

### Reusable Open-Source Components

1. **RSSHub** (AGPL-3.0) -- Self-host as our content source adapter. 1,000+ routes.
2. **RSS-Bridge** (Public Domain) -- Supplement RSSHub. CssSelectorBridge for arbitrary sites.
3. **React-Grid-Layout** (MIT) -- Drop-in grid engine for drag-and-drop dashboard.
4. **GridStack.js** (MIT) -- Alternative grid engine if we need framework flexibility.
5. **FreshRSS extensions** (AGPL-3.0) -- Reference for feed parsing, WebSub, scraping patterns.

---

## 9. Gap Analysis: What None of These Do

No existing project combines ALL of these features:

| Feature | Closest Project | Gap |
|---------|----------------|-----|
| Drag-and-drop widget grid | Homarr, Grafana | Not for content feeds |
| Multi-source content (RSS + social + email + video) | Glance | Missing email, LinkedIn, Instagram, Facebook |
| User-customizable layout at runtime | Homarr | Limited to service widgets |
| Content from ANY website | RSS-Bridge CssSelectorBridge | No dashboard UI |
| AI summarization of feeds | RSSbrew | No visual dashboard |
| Social media feed reading | NewsBlur (limited) | No Instagram/LinkedIn/Facebook |
| Email newsletter aggregation | Feedbin | No grid dashboard |
| Mobile-friendly responsive grid | React-Grid-Layout | Library only, not a product |
| Multi-user with personalized dashboards | FreshRSS, Homarr | Not combined with grid + multi-source |

### The Opportunity

**Glance** (31.9K stars) proves massive demand for a multi-source feed dashboard.
**Homarr** (3K stars, very active) proves drag-and-drop grids work for dashboards.
**RSSHub** (41.8K stars) proves any content can be normalized to RSS.
**React-Grid-Layout** (22.1K stars) provides the drag-and-drop grid engine.

**No one has combined these four ideas into a single product.** That is our opportunity:

> A Glance-like multi-source content dashboard + Homarr-like drag-and-drop grid +
> RSSHub-powered universal content normalization + React-Grid-Layout for the frontend.

This is a greenfield opportunity with proven demand (Glance 31.9K stars) and
proven building blocks (RSSHub, React-Grid-Layout, RSS-Bridge).

---

## Appendix: Star Count Summary (sorted descending)

| Project | Stars | Category | License |
|---------|-------|----------|--------|
| Grafana | 72,100 | Monitoring Dashboard | AGPL-3.0 |
| RSSHub | 41,800 | RSS Generator | AGPL-3.0 |
| Glance | 31,900 | Content Aggregator | AGPL-3.0 |
| Glances | 31,600 | System Monitor | LGPL-3.0 |
| Homepage | 28,400 | Dashboard Launcher | GPL-3.0 |
| Dashy | 24,000 | Dashboard Launcher | MIT |
| React-Grid-Layout | 22,100 | Grid Library | MIT |
| FreshRSS | 14,000 | RSS Reader | AGPL-3.0 |
| Homer | 11,100 | Dashboard Launcher | Apache-2.0 |
| Muuri | ~11,000 | Grid Library | MIT |
| Heimdall | 9,000 | Dashboard Launcher | MIT |
| Miniflux | 8,800 | RSS Reader | Apache-2.0 |
| RSS-Bridge | 8,700 | RSS Generator | Unlicense |
| GridStack.js | 8,700 | Grid Library | MIT |
| NewsBlur | 7,300 | RSS Reader | MIT |
| Flame | 6,200 | Dashboard Launcher | MIT |
| Organizr | 5,700 | Dashboard Launcher | GPL-3.0 |
| Stringer | 3,800 | RSS Reader | MIT |
| Yarr | 3,700 | RSS Reader | MIT |
| Feedbin | 3,700 | RSS Reader | MIT |
| CommaFeed | 3,400 | RSS Reader | Apache-2.0 |
| Homarr | 3,000+ | Dashboard Launcher | Apache-2.0 |
| Tiny Tiny RSS | ~600 | RSS Reader | GPL-3.0 |
| RSSbrew | 268 | Content Aggregator | AGPL-3.0 |
