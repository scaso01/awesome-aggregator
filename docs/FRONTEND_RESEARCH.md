# Frontend Library Research: Awesome Aggregator

> **Date:** 2026-02-12
> **Purpose:** Evaluate free/open-source frontend libraries for building a customizable content dashboard with drag-and-drop grid layout, real-time updates, and dark theme support.
> **Current Stack:** React 19, Vite 6, react-grid-layout 1.5, native WebSocket, CSS variables
> **Constraints:** MIT/free license, minimal dependencies, small bundle size, personal dashboard use case

---

## 1. Grid/Layout Libraries

### Comparison Matrix

| Library | License | Bundle (gz) | NPM Weekly DL | Stars | React 19 | DnD | Resize | Breakpoints |
|---------|---------|-------------|---------------|-------|----------|-----|--------|-------------|
| react-grid-layout | MIT | ~17 kB | ~1.6M | 21.5K | v2.x Yes | Yes | Yes | Yes |
| gridstack.js | MIT | ~25 kB | ~310K | 6.5K | Via wrapper | Yes | Yes | Partial |
| muuri | MIT | ~22 kB | ~30K | 10.9K | Stale wrapper | Yes | No | Via CSS |
| packery | MIT (v3) | ~10 kB | ~15K | 4K | Stale wrapper | Yes | No | Via CSS |
| dnd-kit | MIT | ~10 kB core | Millions | 14K+ | Yes | Yes | DIY | DIY |

### react-grid-layout (CURRENT v1.5.0)

**Strengths:**
- Purpose-built for dashboard grid layouts (exactly our use case)
- Built-in drag-and-drop, resize handles, collision detection, reflow
- Layout serialization for persistence (critical for saving user layouts)
- Responsive breakpoints with per-breakpoint layouts
- 1.6M weekly downloads, massive community
- v2.x rewrite: full TypeScript, hooks API (useGridLayout, useContainerWidth, useResponsiveLayout)
- 100% backwards compatibility via react-grid-layout/legacy

**Weaknesses:**
- v1.x uses class components internally (we have v1.5.0)
- React 19 key-prop warnings on v1.x
- Requires upgrading to v2.x for modern React patterns

**React 19:** v2.2.2 (Jan 2026) rewrote internals with hooks. Full React 18/19 support.

**Verdict:** KEEP AND UPGRADE to v2.x. The v2 rewrite resolves all React 19 concerns.

### gridstack.js

**Strengths:** Pure TypeScript, zero deps, nested grids, enterprise-grade dashboard engine.

**Weaknesses:** React wrapper (react-gridstack) has only ~155 weekly downloads. Cannot reposition at breakpoints. Imperative DOM fights React declarative model.

**Verdict:** Strong core, but React integration is weak. Not worth it when react-grid-layout v2 exists.

### muuri

**Strengths:** Beautiful animations, filtering/sorting, fluid transitions.

**Weaknesses:** muuri-react not updated in 2+ years. No resize handles. 30K vs 1.6M downloads. Better for masonry layouts.

**Verdict:** Wrong paradigm for dashboard grids. Not recommended.

### packery/masonry

**Strengths:** Bin-packing algorithm, Packery v3 MIT, lightweight.

**Weaknesses:** Stale React wrappers, no resize, no layout serialization. Content-flow not dashboard grids.

**Verdict:** Wrong tool for dashboards. Not recommended.

### dnd-kit

**Strengths:** Modern hooks-based API, ~10 kB core, zero deps, excellent accessibility, Feb 2026 release.

**Weaknesses:** DnD primitives ONLY. No grid engine, no resize, no breakpoints, no layout serialization. Would need to build entire dashboard system.

**Verdict:** Low-level toolkit, not a dashboard engine. Keep in mind as supplement for future DnD beyond grid layout.

### GRID RECOMMENDATION

> **Primary: react-grid-layout v2.x** -- Upgrade v1.5 to v2.2.2 for hooks API + React 19.
> **Secondary: dnd-kit** -- For future DnD features beyond grid layout.

---

## 2. UI Component Libraries

### Comparison Matrix

| Library | License | Bundle Approach | Impact | Dark Theme | React 19 | Philosophy |
|---------|---------|----------------|--------|------------|----------|-----------|
| shadcn/ui | MIT | Copy into project | ~150 kB total | Yes (CSS vars) | Yes | Zero dep; Radix + Tailwind |
| Radix UI | MIT | Modular npm | ~2-5 kB each | Unstyled | Yes | Headless primitives |
| Mantine | MIT | npm package | ~140 kB gz full | Yes (toggle) | Yes | Full-featured |
| Chakra UI | MIT | npm package | Reduced in v3 | Yes | v3 Yes | Ark UI powered |
| Ant Design | MIT | npm package | ~120 kB gz + icons | Yes | Yes | Heavy, enterprise |
| Material UI | MIT | npm package | ~80 kB gz | Yes | Yes | Material Design |

### shadcn/ui

**Strengths:**
- Not an npm dependency: you copy component source into your project
- Complete ownership and customization of every component
- Built on Radix UI primitives (accessibility, keyboard nav, screen reader)
- Styled with Tailwind CSS + CSS variables (easy dark theme)
- Modern, polished design aesthetic out of the box
- Zero bundle overhead beyond what you use
- CLI: npx shadcn add button fetches only what you need
- Massive community adoption in 2025-2026

**Weaknesses:**
- Requires Tailwind CSS (~10-30 kB CSS, purged in prod)
- No built-in form validation, notifications, or complex hooks
- Leaner docs, expects source code reading

**React 19:** Fully compatible. Components are just React code in your project.

### Radix UI (Primitives)

Foundation layer powering shadcn/ui. 32+ headless accessible primitives, 130M+ monthly downloads, WAI-ARIA compliant. Use indirectly through shadcn/ui.

### Mantine

**Strengths:** 120+ components + 60+ hooks, dark mode toggle, PostCSS v7 (no CSS-in-JS runtime), tree-shakeable.

**Weaknesses:** Library dependency model, larger baseline bundle, enterprise aesthetic, v7 migration was painful.

### Chakra UI

v3 dropped framer-motion (smaller), now Ark UI powered. But v3 had massive breaking changes, community fragmented v2/v3. Not ideal for new project.

### Ant Design

Heavy (~120 kB gz + icons/Moment.js). Enterprise-focused overkill for personal dashboard.

### Material UI

Material Design hard to customize away from. Emotion runtime dependency. Heavier than Tailwind alternatives.

### UI RECOMMENDATION

> **Primary: shadcn/ui** -- Zero dep, own the source, Radix accessibility, Tailwind styling, only what we use.
>
> Why not Mantine? For max panel customization, owning component source beats 120 pre-built components. Can add @mantine/hooks later.

---

## 3. Real-Time / Data Fetching

### Comparison Matrix

| Library | License | Bundle | Use Case | WebSocket | Caching |
|---------|---------|--------|----------|-----------|---------|
| Native WebSocket | Built-in | 0 kB | Low-level bidirectional | IS the WebSocket | None |
| Socket.IO Client | MIT | ~45 kB gz | Reliable bidir + rooms | WS + fallbacks | None |
| TanStack Query | MIT | ~13 kB gz | Server state mgmt | Via invalidation | Yes (SWR) |
| SWR | MIT | ~4 kB gz | Server state mgmt | Via mutation | Yes (SWR) |

### Native WebSocket (CURRENT)

Zero bundle cost, max performance, full control. Already in our FastAPI backend. Missing reconnection logic (~20 lines). Fine for single-user localhost/LAN.

### Socket.IO

Auto-reconnection, fallback to long-polling, rooms/namespaces. But ~45 kB for features we do not need. Requires replacing FastAPI WS with python-socketio. **Overkill** for single-user dashboard.

### TanStack Query (React Query)

**Strengths:**
- Stale-while-revalidate caching, background refetch, cache invalidation
- WebSocket integration: WS event triggers queryClient.invalidateQueries()
- If panel visible, auto-refetches; if not, lazy refetch on navigation
- DevTools for cache debugging, ~13 kB gz, actively maintained

**Weaknesses:** Not a WS replacement (complements it). Cache key learning curve.

**WebSocket Integration Pattern:**


### SWR

Tiny (~4 kB) but fewer features than TanStack Query. Missing devtools, less robust mutations. TanStack Query worth the extra ~9 kB.

### REAL-TIME RECOMMENDATION

> **Keep: Native WebSocket** with reconnection wrapper.
> **Add: TanStack Query** for caching + WebSocket invalidation pattern.

---

## 4. Theming / CSS

### Comparison Matrix

| Approach | License | Bundle | Scoping | Dark Theme | Learning Curve |
|----------|---------|--------|---------|------------|---------------|
| Tailwind CSS | MIT | ~10-30 kB (purged) | Utility classes | dark: prefix | Medium |
| CSS Modules | Built-in | 0 kB runtime | Scoped default | Manual | Low |
| Styled Components | MIT | ~12 kB runtime | Scoped | ThemeProvider | Medium |
| CSS Variables | Built-in | 0 kB runtime | Global | Class toggle | Low |

### Summary

- **Tailwind CSS:** JIT produces tiny prod bundles. dark: prefix trivial. Massive ecosystem (shadcn built on it). Required by shadcn/ui. Excellent Vite integration.
- **CSS Modules:** Zero runtime, scoped by default. Good companion.
- **Styled Components:** Runtime CSS-in-JS declining. Not recommended for new projects.
- **CSS Variables:** Keep as underlying theme token mechanism.

### CSS RECOMMENDATION

> **Primary: Tailwind CSS** -- Required by shadcn/ui, best dark theme DX.
> **Keep: CSS Variables** as theme token layer (standard shadcn pattern).
> **Hybrid:** Tailwind for components, CSS Variables for tokens, CSS Modules for complex one-offs.

---

## 5. State Management

### Comparison Matrix

| Library | License | Bundle | Weekly DL | Provider? | DevTools | Boilerplate |
|---------|---------|--------|-----------|-----------|----------|-------------|
| React Context | Built-in | 0 kB | N/A | Yes | React DT | Low |
| Zustand | MIT | ~3 kB gz | ~15-19M | No | Middleware | Minimal |
| Jotai | MIT | ~4 kB gz | ~2-3M | Optional | Yes | Minimal |
| Redux Toolkit | MIT | ~11 kB gz | Very high | Yes | Excellent | Moderate |

### React Context

Zero cost, familiar. Good for low-frequency state (theme, settings). Bad for frequent updates (re-renders all consumers).

### Zustand

**Strengths:**
- ~3 kB gz, nearly as lightweight as possible
- No Provider required, just import and use
- Selector-based subscriptions prevent unnecessary re-renders
- Simple API: create((set) => ({ ... }))
- Middleware: persist (localStorage), devtools, immer
- 15-19M weekly downloads, well-maintained
- Can be used OUTSIDE React components (WebSocket handlers)

**Weaknesses:** Manual selector optimization, single store model (but multiple stores OK).

### Jotai

~4 kB, atom-based fine-grained reactivity. Excellent but atom model less natural for our interconnected dashboard state (sources, layouts, views, content). Zustand store model fits better.

### Redux Toolkit

~11 kB (3-4x Zustand). Provider wrapping. More boilerplate. Overkill for single-user dashboard.

### STATE RECOMMENDATION

> **Primary: Zustand** -- 3 kB, no Provider, WS handler compatible, persist middleware.
> **Keep: React Context** for rarely-changing globals (theme, user settings).
>
> Store architecture:
> - useSourceStore -- Sources, config, refresh status
> - useContentStore -- Cached content per source
> - useLayoutStore -- Grid positions (with persist middleware)
> - useViewStore -- Named views/workspaces

---

## 6. Final Recommendations

### Recommended Stack

| Category | Choice | Rationale |
|----------|--------|-----------|
| Grid Layout | react-grid-layout v2.x | Dashboard-specific. Upgrade v1.5 to v2.2.2 |
| UI Components | shadcn/ui | Zero dep, own source, Radix a11y, Tailwind |
| Data Fetching | TanStack Query | Smart caching + WS invalidation pattern |
| Real-Time | Native WebSocket + reconnect | Already working, no Socket.IO overhead |
| CSS/Theming | Tailwind CSS + CSS Variables | Required by shadcn/ui, dark: prefix |
| State Mgmt | Zustand | 3 kB, no Provider, WS compatible, persist |

### Migration Path

| Current | Recommended |
|---------|-------------|
| react-grid-layout 1.5.0 | react-grid-layout 2.2.2 |
| (no UI library) | shadcn/ui (add incrementally) |
| Native WebSocket | Native WebSocket (keep) + TanStack Query |
| CSS Variables | Tailwind CSS + CSS Variables |
| (no state management) | Zustand |
| React 19 | React 19 (keep) |
| Vite 6 | Vite 6 (keep) |

### New Dependencies (Bundle Impact)

| Package | Size (min+gz) |
|---------|--------------|
| react-grid-layout v2 | ~17 kB (upgrading from v1) |
| @tanstack/react-query | ~13 kB |
| zustand | ~3 kB |
| tailwindcss | ~10-30 kB CSS (zero JS runtime) |
| shadcn/ui components | ~2-5 kB per component |
| **Total new JS** | **~33 kB gz** |

### Exclusions

| Library | Reason |
|---------|--------|
| Socket.IO | Solves problems we do not have. Would replace working FastAPI WS. |
| gridstack.js | Poor React integration. Community wrappers unreliable. |
| muuri | Stale React wrappers. Masonry not dashboard. |
| Mantine | Prefer owning source (shadcn). Can add @mantine/hooks later. |
| Chakra UI | v3 breaking changes fragmented community. |
| Ant Design | ~120 kB+, enterprise overkill. |
| Material UI | Material Design does not fit. Emotion runtime dep. |
| Redux Toolkit | 3-4x heavier. Provider ceremony. Overkill. |
| Styled Components | Runtime CSS-in-JS declining. |
| Jotai | Atom model less natural for interconnected state. |
| SWR | Fewer features than TanStack Query for ~9 kB savings. |

---

## Sources

### Grid/Layout
- npm trends: https://npmtrends.com/gridstack-vs-gridster-vs-muuri-vs-react-grid-layout
- react-grid-layout: https://github.com/react-grid-layout/react-grid-layout
- react-grid-layout releases: https://github.com/react-grid-layout/react-grid-layout/releases
- react-grid-layout-19 fork: https://github.com/Censkh/react-grid-layout-19
- gridstack.js: https://gridstackjs.com/
- dnd-kit: https://docs.dndkit.com
- Gridstack dashboards: https://blog.openreplay.com/building-interactive-dashboards-with-gridstack-js/
- Top 5 DnD 2026: https://puckeditor.com/blog/top-5-drag-and-drop-libraries-for-react

### UI Components
- React UI libs 2025: https://makersden.io/blog/react-ui-libs-2025-comparing-shadcn-radix-mantine-mui-chakra
- Mantine vs shadcn 2026: https://saasindie.com/blog/mantine-vs-shadcn-ui-comparison
- Best React UI 2026: https://www.untitledui.com/blog/react-component-libraries
- shadcn/ui: https://ui.shadcn.com/
- Radix vs shadcn: https://saasindie.com/blog/shadcn-vs-radix-themes-comparison
- Chakra v3: https://chakra-ui.com/blog/announcing-v3

### State Management
- Zustand vs Redux vs Jotai: https://betterstack.com/community/guides/scaling-nodejs/zustand-vs-redux-toolkit-vs-jotai/
- State Mgmt 2025: https://www.meerako.com/blogs/react-state-management-zustand-vs-redux-vs-context-2025
- State Mgmt 2026: https://www.syncfusion.com/blogs/post/react-state-management-libraries

### Real-Time
- WS + React Query: https://tkdodo.eu/blog/using-web-sockets-with-react-query
- TanStack + WS: https://blog.logrocket.com/tanstack-query-websockets-real-time-react-data-fetching/
- Socket.IO vs WS: https://velt.dev/blog/socketio-vs-websocket-guide-developers

### CSS
- CSS comparison: https://medium.com/@ignatovich.dm/css-modules-vs-css-in-js-vs-tailwind-css-a-comprehensive-comparison-24e7cb6f48e9
- React CSS 2026: https://medium.com/@imranmsa93/react-css-in-2026-best-styling-approaches-compared-d5e99a771753
