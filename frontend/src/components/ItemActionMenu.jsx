import React, { useState, useEffect, useRef } from 'react'

const API_BASE = '/api'

export default function ItemActionMenu({ item, onBookmark, onHideItem, onMuteSource }) {
  const [open, setOpen] = useState(false)
  const [showMuteSub, setShowMuteSub] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false)
        setShowMuteSub(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const handleBookmark = async () => {
    try {
      // POST /api/bookmarks/, not /api/actions/bookmark. There has never been a
      // bookmark route on the actions router, so this used to fail and the catch
      // below swallowed it: the menu closed and nothing was ever saved.
      const res = await fetch(`${API_BASE}/bookmarks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content_item_id: item.id,
          source_id: item.source_id,
          title: item.title,
          url: item.url,
          image_url: item.image_url || null,
        }),
      })
      if (!res.ok) throw new Error(`Bookmark failed: ${res.status}`)
      if (onBookmark) onBookmark(item.id)
    } catch (err) { console.error('Bookmark failed:', err) }
    setOpen(false)
  }

  const handleHide = async () => {
    try {
      // The field is content_item_id. Sending item_id got a 422 every time.
      const res = await fetch(`${API_BASE}/actions/hide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content_item_id: item.id }),
      })
      if (!res.ok) throw new Error(`Hide failed: ${res.status}`)
      if (onHideItem) onHideItem(item.id)
    } catch (err) { console.error('Hide failed:', err) }
    setOpen(false)
  }

  const handleMute = async (duration) => {
    try {
      await fetch(`${API_BASE}/actions/mute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: item.source_id, duration }),
      })
      if (onMuteSource) onMuteSource(item.source_id, duration)
    } catch (err) { console.error('Mute failed:', err) }
    setOpen(false)
    setShowMuteSub(false)
  }

  return (
    <div ref={menuRef}>
      <button className="item-action-trigger" onClick={(e) => { e.stopPropagation(); setOpen(!open) }}>
        &#8943;
      </button>
      {open && (
        <div className="item-action-menu">
          <button className="item-action-option" onClick={handleBookmark}>
            Bookmark
          </button>
          <button className="item-action-option" onClick={handleHide}>
            Hide this item
          </button>
          <button className="item-action-option" onClick={() => setShowMuteSub(!showMuteSub)}>
            Mute source
          </button>
          {showMuteSub && (
            <div className="item-action-submenu">
              <button className="item-action-option" onClick={() => handleMute('24h')}>24 hours</button>
              <button className="item-action-option" onClick={() => handleMute('1w')}>1 week</button>
              <button className="item-action-option" onClick={() => handleMute('1m')}>1 month</button>
              <button className="item-action-option" onClick={() => handleMute('permanent')}>Permanent</button>
            </div>
          )}
          <a href={item.url} target="_blank" rel="noopener noreferrer"
            className="item-action-option" style={{ display: 'block', textDecoration: 'none', color: 'inherit' }}>
            Open in new tab
          </a>
        </div>
      )}
    </div>
  )
}
