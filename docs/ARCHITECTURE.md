# Awesome Aggregator - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (React + Vite)                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Dashboard Grid (react-grid-layout)                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │ YouTube  │ │ Reddit   │ │ Hacker   │ │ RSS Feed │   │   │
│  │  │ Panel    │ │ Panel    │ │ News     │ │ Panel    │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│          │ REST API                    ▲ WebSocket               │
└──────────┼─────────────────────────────┼────────────────────────┘
           │                             │
┌──────────▼─────────────────────────────┼────────────────────────┐
│  BACKEND (FastAPI)                     │                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─┴────────────┐           │
│  │ REST API    │  │ Scheduler    │  │ WebSocket    │           │
│  │ /api/*      │  │ (APScheduler)│  │ Manager      │           │
│  └──────┬──────┘  └──────┬───────┘  └──────────────┘           │
│         │                │                                       │
│  ┌──────▼───────────────▼────────────────────────────────┐      │
│  │  Source Adapters (Plugin Pattern)                       │      │
│  │  ┌────────┐ ┌─────────┐ ┌────────┐ ┌─────────┐       │      │
│  │  │  RSS   │ │ YouTube │ │ Reddit │ │ Generic │       │      │
│  │  │Adapter │ │ Adapter │ │Adapter │ │ Adapter │       │      │
│  │  └────────┘ └─────────┘ └────────┘ └─────────┘       │      │
│  └────────────────────────┬──────────────────────────────┘      │
│                           │                                       │
│  ┌────────────────────────▼──────────────────────────────┐      │
│  │  Data Layer                                            │      │
│  │  ┌──────────┐  ┌────────────┐  ┌───────────────┐     │      │
│  │  │ SQLite   │  │ In-Memory  │  │ Content Cache │     │      │
│  │  │ Database │  │ Cache      │  │ (TTL-based)   │     │      │
│  │  └──────────┘  └────────────┘  └───────────────┘     │      │
│  └────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Source Adapter Pattern
All content sources implement `BaseSource` with a `fetch()` method. New source types are added by:
1. Creating a new file in `backend/sources/`
2. Inheriting from `BaseSource`
3. Registering in `SOURCE_REGISTRY`

This keeps source-specific logic isolated and makes the system extensible.

### 2. Real-Time via WebSocket
Content updates push to the frontend via WebSocket rather than polling. Benefits:
- Instant updates when new content arrives
- Lower server load (no repeated polling)
- Source status changes (error/recovered) propagate immediately

### 3. SQLite for Simplicity
SQLite was chosen over PostgreSQL because:
- Zero configuration (no server to run)
- Single file, easy to backup/reset
- Sufficient for personal use (50-100 sources, ~10K items)
- WAL mode enables concurrent reads during writes

### 4. APScheduler for Background Refresh
Per-source refresh intervals managed by APScheduler:
- Each source gets its own job with configurable interval
- Jobs run immediately on creation (first fetch)
- Failed fetches mark the source as "error" without stopping other sources

### 5. Free-Only APIs
All content fetching uses free, unlimited endpoints:
- **YouTube:** RSS feed (`/feeds/videos.xml?channel_id=...`) - no API key
- **Reddit:** `.json` endpoints - no auth required
- **RSS:** Standard feed parsing - universally supported
- **Generic:** Web scraping via trafilatura - works on any page

### 6. React Grid Layout
react-grid-layout provides:
- Drag-and-drop repositioning
- Resize handles on panels
- Responsive breakpoints
- Collision detection and reflow
- Layout serialization for persistence

## Data Models

### Sources Table
```sql
sources(id, name, source_type, url, refresh_seconds,
        display_format, category, status, last_fetched,
        last_error, item_count, created_at, updated_at)
```

### Content Items Table
```sql
content_items(id, source_id, title, url, description,
              image_url, author, published_at, fetched_at, metadata)
-- UNIQUE(source_id, url) for upsert deduplication
```

### Layouts Table
```sql
layouts(id, name, panels_json, created_at, updated_at)
-- panels_json: [{source_id, x, y, w, h}, ...]
```

### Views Table
```sql
views(id, name, description, source_ids_json, layout_id,
      created_at, updated_at)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sources/` | List all sources |
| POST | `/api/sources/` | Add a new source |
| GET | `/api/sources/{id}` | Get source details |
| PATCH | `/api/sources/{id}` | Update source config |
| DELETE | `/api/sources/{id}` | Delete source + content |
| GET | `/api/content/` | Get all content (feed) |
| GET | `/api/content/source/{id}` | Get content for one source |
| GET | `/api/layouts/{name}` | Get saved layout |
| PUT | `/api/layouts/{name}` | Save/update layout |
| GET | `/api/views/` | List named views |
| POST | `/api/views/` | Create a named view |
| GET | `/api/views/{id}` | Get view details |
| WS | `/ws` | Real-time updates |
| GET | `/api/health` | Health check |

## Future Architecture Considerations

- **Plugin System:** Source adapters could be loaded dynamically from a `plugins/` directory
- **Worker Processes:** For 100+ sources, the scheduler could offload to background workers
- **Redis Cache:** If performance needs grow beyond SQLite's capabilities
- **Authentication:** Optional auth layer for multi-user deployments
