import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

import ContentPanel from './components/ContentPanel'
import OnboardingPicker from './components/OnboardingPicker'
import AddSourceModal from './components/AddSourceModal'
import TabBar from './components/TabBar'
import ViewEditor from './components/ViewEditor'
import DigestView from './components/DigestView'
import ReaderMode from './components/ReaderMode'
import ReadingStats from './components/ReadingStats'
import MutedSources from './components/MutedSources'

const ResponsiveGridLayout = WidthProvider(Responsive)

const API_BASE = '/api'

function App() {
  const [sources, setSources] = useState([])
  const [content, setContent] = useState({})
  const [layout, setLayout] = useState([])
  const [showAddModal, setShowAddModal] = useState(false)
  const [showHidden, setShowHidden] = useState(false)
  const [viewerUrl, setViewerUrl] = useState(null)
  const [viewerTitle, setViewerTitle] = useState('')
  const [viewerItem, setViewerItem] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [showMuted, setShowMuted] = useState(false)
  const [opmlStatus, setOpmlStatus] = useState('')
  const wsRef = useRef(null)
  const opmlInputRef = useRef(null)

  // View/tab state
  const [views, setViews] = useState([])
  const [activeViewId, setActiveViewId] = useState(null)
  const [showViewEditor, setShowViewEditor] = useState(false)
  const [editingView, setEditingView] = useState(null)
  const [viewContent, setViewContent] = useState([])

  // The item is optional so callers that only have a URL still work. Reader mode
  // needs it to bookmark, because a bookmark is keyed on the content item.
  const openViewer = (url, title, item = null) => {
    setViewerUrl(url)
    setViewerTitle(title || '')
    setViewerItem(item)
  }

  useEffect(() => {
    fetchSources()
    fetchViews()
    connectWebSocket()
    return () => { if (wsRef.current) wsRef.current.close() }
  }, [])

  useEffect(() => {
    sources.forEach(source => fetchContent(source.id))
  }, [sources])

  // Fetch view content when activeViewId changes.
  //
  // The bookmarks tab used to fall through here, because this only ran for a
  // numeric id. Nothing fetched, so the tab either sat on "No bookmarks yet"
  // forever or, worse, kept showing whichever custom view was open last and
  // presented those items as bookmarks.
  useEffect(() => {
    if (typeof activeViewId === 'number') {
      fetchViewContent(activeViewId)
    } else if (activeViewId === 'bookmarks') {
      fetchBookmarks()
    } else {
      setViewContent([])
    }
  }, [activeViewId])

  const fetchSources = async () => {
    try {
      const res = await fetch(`${API_BASE}/sources/`)
      const data = await res.json()
      setSources(data)
      if (data.length === 0) {
        setShowOnboarding(true)
      } else {
        setShowOnboarding(false)
      }
      const active = data.filter(s => s.status !== 'paused')
      if (active.length > 0) {
        // Start from the default 3-up arrangement, then let any saved layout
        // override it. onLayoutChange has always PUT the layout to the server,
        // but nothing ever read it back, so dragging and resizing survived until
        // the next reload and no further.
        const fallback = active.map((src, i) => ({
          i: String(src.id),
          x: (i % 3) * 4, y: Math.floor(i / 3) * 4,
          w: 4, h: 4, minW: 2, minH: 2,
        }))
        setLayout(await mergeSavedLayout(fallback))
      }
    } catch (err) { console.error('Failed to fetch sources:', err) }
    finally { setLoading(false) }
  }

  // Overlay the saved layout onto the default arrangement. A source with no
  // saved panel keeps its default slot, so adding a source does not disturb the
  // ones already placed. A 404 means nothing has been saved yet, which is the
  // normal first-run case.
  const mergeSavedLayout = async (fallback) => {
    try {
      const res = await fetch(`${API_BASE}/layouts/default`)
      if (!res.ok) return fallback
      const saved = await res.json()
      const byId = new Map((saved.panels || []).map(p => [String(p.source_id), p]))
      return fallback.map(panel => {
        const p = byId.get(panel.i)
        return p ? { ...panel, x: p.x, y: p.y, w: p.w, h: p.h } : panel
      })
    } catch (err) {
      console.error('Failed to load saved layout:', err)
      return fallback
    }
  }

  const fetchContent = async (sourceId) => {
    try {
      const res = await fetch(`${API_BASE}/content/source/${sourceId}?limit=20`)
      const data = await res.json()
      setContent(prev => ({ ...prev, [sourceId]: data }))
    } catch (err) { console.error(`Failed to fetch content for source ${sourceId}:`, err) }
  }

  const fetchViews = async () => {
    try {
      const res = await fetch(`${API_BASE}/views/`)
      if (res.ok) {
        const data = await res.json()
        setViews(data)
      }
    } catch (err) { console.error('Failed to fetch views:', err) }
  }

  const fetchViewContent = async (viewId) => {
    try {
      const res = await fetch(`${API_BASE}/content/view/${viewId}`)
      if (res.ok) {
        const data = await res.json()
        setViewContent(data)
      }
    } catch (err) { console.error('Failed to fetch view content:', err) }
  }

  const fetchBookmarks = async () => {
    try {
      const res = await fetch(`${API_BASE}/bookmarks/`)
      if (res.ok) setViewContent(await res.json())
    } catch (err) { console.error('Failed to fetch bookmarks:', err) }
  }

  const removeBookmark = async (bookmarkId) => {
    try {
      const res = await fetch(`${API_BASE}/bookmarks/${bookmarkId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`Remove failed: ${res.status}`)
      setViewContent(prev => prev.filter(b => b.id !== bookmarkId))
    } catch (err) { console.error('Failed to remove bookmark:', err) }
  }

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`)
    wsRef.current = ws
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'new_content') fetchContent(msg.source_id)
        else if (msg.type === 'source_update')
          setSources(prev => prev.map(s =>
            s.id === msg.source_id ? { ...s, status: msg.status, last_error: msg.error } : s
          ))
      } catch (err) { console.error('WebSocket parse error:', err) }
    }
    ws.onclose = () => setTimeout(connectWebSocket, 3000)
    ws.onerror = (err) => console.error('WebSocket error:', err)
  }

  // Export is a plain link, because the endpoint already sends a
  // Content-Disposition header and the browser knows what to do with it.
  // Import needs the file, so it goes through a hidden input.
  const importOpml = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    setOpmlStatus('Importing...')
    const body = new FormData()
    body.append('file', file)
    try {
      // No Content-Type header: fetch has to set it itself so the multipart
      // boundary matches the body, and naming it by hand breaks the upload.
      const res = await fetch(`${API_BASE}/opml/import`, { method: 'POST', body })
      if (!res.ok) throw new Error(`Import failed (${res.status})`)
      const result = await res.json()
      setOpmlStatus(`Imported ${result.imported}, skipped ${result.skipped}`)
      fetchSources()
    } catch (err) {
      setOpmlStatus(err.message)
    } finally {
      // Clearing the value lets the same file be picked again straight after.
      event.target.value = ''
      // The result is a notice, not a permanent part of the header.
      setTimeout(() => setOpmlStatus(''), 8000)
    }
  }

  const addSource = async (sourceData) => {
    try {
      const res = await fetch(`${API_BASE}/sources/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sourceData),
      })
      if (res.ok) { setShowAddModal(false); fetchSources() }
    } catch (err) { console.error('Failed to add source:', err) }
  }

  const batchAddSources = async (sourcesArray) => {
    try {
      const payload = {
        sources: sourcesArray.map(s => ({
          name: s.name,
          source_type: s.type,
          url: s.url,
          refresh_seconds: 300,
          display_format: 'compact',
          category: s.category || 'General',
        })),
      }
      const res = await fetch(`${API_BASE}/sources/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        const result = await res.json()
        fetchSources()
        return result
      }
    } catch (err) { console.error('Failed to batch add sources:', err) }
    return null
  }

  const updateSource = async (sourceId, updates) => {
    try {
      await fetch(`${API_BASE}/sources/${sourceId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      setSources(prev => prev.map(s => s.id === sourceId ? { ...s, ...updates } : s))
    } catch (err) { console.error('Failed to update source:', err) }
  }

  const hideSource = async (sourceId) => {
    try {
      await fetch(`${API_BASE}/sources/${sourceId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'paused' }),
      })
      setSources(prev => prev.map(s => s.id === sourceId ? { ...s, status: 'paused' } : s))
    } catch (err) { console.error('Failed to hide source:', err) }
  }

  const unhideSource = async (sourceId) => {
    try {
      await fetch(`${API_BASE}/sources/${sourceId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'active' }),
      })
      setSources(prev => prev.map(s => s.id === sourceId ? { ...s, status: 'active' } : s))
    } catch (err) { console.error('Failed to unhide source:', err) }
  }

  const deleteSource = async (sourceId) => {
    try {
      await fetch(`${API_BASE}/sources/${sourceId}`, { method: 'DELETE' })
      setSources(prev => prev.filter(s => s.id !== sourceId))
      setContent(prev => { const next = { ...prev }; delete next[sourceId]; return next })
    } catch (err) { console.error('Failed to remove source:', err) }
  }

  const onLayoutChange = (newLayout) => {
    setLayout(newLayout)
    fetch(`${API_BASE}/layouts/default`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'default',
        panels: newLayout.map(l => ({ source_id: parseInt(l.i), x: l.x, y: l.y, w: l.w, h: l.h })),
      }),
    }).catch(err => console.error('Failed to save layout:', err))
  }

  const formatTime = (isoString) => {
    if (!isoString) return ''
    const diffMs = Date.now() - new Date(isoString)
    const mins = Math.floor(diffMs / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  }

  const handleSelectView = (viewId) => {
    setActiveViewId(viewId)
  }

  const handleCreateView = () => {
    setEditingView(null)
    setShowViewEditor(true)
  }

  const handleReorderViews = async (orderedIds) => {
    // Optimistic reorder
    const reordered = orderedIds.map(id => views.find(v => v.id === id)).filter(Boolean)
    setViews(reordered)
    try {
      // PUT, and the field is view_ids. This was a POST carrying {order: [...]},
      // so dragging a tab to a new position did nothing at all: wrong method,
      // and the right method would still have rejected the body.
      const res = await fetch(`${API_BASE}/views/reorder`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view_ids: orderedIds }),
      })
      if (!res.ok) throw new Error(`Reorder failed: ${res.status}`)
    } catch (err) { console.error('Failed to reorder views:', err) }
  }

  const activeSources = sources.filter(s => s.status !== 'paused')
  const hiddenSources = sources.filter(s => s.status === 'paused')

  if (loading) return <div className="loading">Loading dashboard...</div>

  // Determine main content based on active view
  const renderMainContent = () => {
    // Digest view
    if (activeViewId === 'digest') {
      return <DigestView openViewer={openViewer} />
    }

    // Bookmarks view -- simple placeholder, content comes from API
    if (activeViewId === 'bookmarks') {
      return (
        <div className="digest-container">
          <div className="digest-header">
            <div className="digest-title">Bookmarks</div>
            <div className="digest-subtitle">Your saved items</div>
          </div>
          {viewContent.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              No bookmarks yet. Use the action menu on items to bookmark them.
            </div>
          ) : (
            viewContent.map((item, idx) => (
              <div key={item.id || idx} className="digest-item">
                <div className="digest-item-content">
                  <div className="digest-item-title">
                    <a href={item.url} onClick={(e) => { e.preventDefault(); openViewer(item.url, item.title, item) }}>
                      {item.title || 'Untitled'}
                    </a>
                  </div>
                  <div className="digest-item-meta">
                    {item.source_name && <span>{item.source_name}</span>}
                    {(item.created_at || item.published_at) &&
                      <span>{formatTime(item.created_at || item.published_at)}</span>}
                  </div>
                </div>
                <button className="btn btn-sm" onClick={() => removeBookmark(item.id)}>
                  Remove
                </button>
              </div>
            ))
          )}
        </div>
      )
    }

    // Custom view -- show filtered content
    if (typeof activeViewId === 'number') {
      return (
        <div className="digest-container">
          {viewContent.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              No items match this view's filters.
            </div>
          ) : (
            viewContent.map((item, idx) => (
              <div key={item.id || idx} className="digest-item">
                <div className="digest-item-content">
                  <div className="digest-item-title">
                    <a href={item.url} onClick={(e) => { e.preventDefault(); openViewer(item.url, item.title, item) }}>
                      {item.title || 'Untitled'}
                    </a>
                  </div>
                  <div className="digest-item-meta">
                    {item.source_name && <span>{item.source_name}</span>}
                    {item.published_at && <span>{formatTime(item.published_at)}</span>}
                  </div>
                </div>
                {item.image_url && (
                  <img className="digest-item-image" src={item.image_url} alt=""
                    onError={e => { e.target.style.display = 'none' }} />
                )}
              </div>
            ))
          )}
        </div>
      )
    }

    // Default "All" view -- the grid
    if (showOnboarding) {
      return (
        <OnboardingPicker
          onComplete={async (selectedSources) => {
            await batchAddSources(selectedSources)
            setShowOnboarding(false)
          }}
          onSkip={() => setShowOnboarding(false)}
        />
      )
    }

    if (!showOnboarding && activeSources.length === 0 && hiddenSources.length === 0) {
      return (
        <div className="empty-state">
          <h2>Welcome to Awesome Aggregator</h2>
          <p>Add your first content source to get started.</p>
          <button className="btn btn-primary" onClick={() => setShowOnboarding(true)}>Choose Topics</button>
          <div style={{ marginTop: '8px' }}>
            <button className="btn" onClick={() => setShowAddModal(true)}>+ Add Source Manually</button>
          </div>
        </div>
      )
    }

    if (!showOnboarding && activeSources.length === 0) {
      return (
        <div className="empty-state">
          <p>All sources are hidden. Click "hidden" above to restore them.</p>
        </div>
      )
    }

    return (
      <div className="dashboard-grid">
        <ResponsiveGridLayout
          className="layout"
          layouts={{ lg: layout }}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480 }}
          cols={{ lg: 12, md: 9, sm: 6, xs: 3 }}
          rowHeight={100}
          onLayoutChange={onLayoutChange}
          draggableHandle=".panel-drag-handle"
          isResizable={true}
          isDraggable={true}
          compactType="vertical"
        >
          {activeSources.map(source => (
            <div key={String(source.id)}>
              <ContentPanel
                source={{ ...source, custom_style: JSON.parse(localStorage.getItem(`panel_style_${source.id}`) || '{}') }}
                items={content[source.id] || []}
                onHide={() => hideSource(source.id)}
                onUpdateSource={(updates, customStyle) => {
                  updateSource(source.id, updates)
                  if (customStyle) {
                    localStorage.setItem(`panel_style_${source.id}`, JSON.stringify(customStyle))
                    setSources(prev => prev.map(s => s.id === source.id ? { ...s, ...updates } : s))
                  }
                }}
                openViewer={openViewer}
                formatTime={formatTime}
                onHideItem={(itemId) => setContent(prev => ({
                  ...prev,
                  [source.id]: (prev[source.id] || []).filter(i => i.id !== itemId),
                }))}
                onMuteSource={(sourceId) => setSources(prev => prev.filter(s => s.id !== sourceId))}
              />
            </div>
          ))}
        </ResponsiveGridLayout>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="app-title">Awesome Aggregator</span>
          <span className="app-subtitle">{activeSources.length} sources</span>
        </div>
        <div className="header-actions">
          {hiddenSources.length > 0 && (
            <button className="btn" onClick={() => setShowHidden(!showHidden)}>
              {hiddenSources.length} hidden
            </button>
          )}
          {opmlStatus && <span className="opml-status">{opmlStatus}</span>}
          <input
            ref={opmlInputRef}
            type="file"
            accept=".opml,.xml,text/xml,application/xml"
            onChange={importOpml}
            style={{ display: 'none' }}
          />
          <button className="btn" onClick={() => opmlInputRef.current?.click()}>Import</button>
          <a className="btn" href={`${API_BASE}/opml/export`} download>Export</a>
          <button className="btn" onClick={() => setShowMuted(true)}>Muted</button>
          <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>+ Add Source</button>
        </div>
      </header>

      <TabBar
        views={views}
        activeViewId={activeViewId}
        onSelectView={handleSelectView}
        onCreateView={handleCreateView}
        onReorderViews={handleReorderViews}
      />

      <ReadingStats />

      {/* Hidden sources tray */}
      {showHidden && hiddenSources.length > 0 && (
        <div className="hidden-tray">
          {hiddenSources.map(source => (
            <div key={source.id} className="hidden-source">
              <span className="hidden-source-name">{source.name}</span>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button className="btn btn-sm" onClick={() => unhideSource(source.id)}>Show</button>
                <button className="btn btn-sm btn-danger" onClick={() => deleteSource(source.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {renderMainContent()}

      {showAddModal && <AddSourceModal onAdd={addSource} onBatchAdd={batchAddSources} onClose={() => setShowAddModal(false)} />}
      {showMuted && (
        <MutedSources onClose={() => { setShowMuted(false); fetchSources() }} />
      )}
      {viewerUrl && (
        <ReaderMode
          url={viewerUrl}
          title={viewerTitle}
          item={viewerItem}
          onClose={() => { setViewerUrl(null); setViewerItem(null) }}
        />
      )}
      {showViewEditor && (
        <ViewEditor
          view={editingView}
          sources={sources}
          onSave={() => { setShowViewEditor(false); fetchViews() }}
          onClose={() => setShowViewEditor(false)}
        />
      )}
    </div>
  )
}

export default App
