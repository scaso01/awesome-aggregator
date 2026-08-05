import React, { useState, useEffect } from 'react'

const API_BASE = '/api'

export default function DigestView({ openViewer }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchDigest = async () => {
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE}/digest/today`)
        if (res.ok) {
          const data = await res.json()
          // The endpoint returns [{rank, content_item, score}], so the fields
          // this view renders live one level down. Reading them off the wrapper
          // made every row show "Untitled" with no link and no timestamp.
          const list = Array.isArray(data) ? data : (data.items || [])
          setItems(list.map(entry => (
            entry && entry.content_item
              ? { ...entry.content_item, score: entry.score, rank: entry.rank }
              : entry
          )))
        }
      } catch (err) { console.error('Failed to fetch digest:', err) }
      finally { setLoading(false) }
    }
    fetchDigest()
  }, [])

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

  if (loading) {
    return (
      <div className="digest-container">
        <div className="loading" style={{ padding: '40px' }}>Loading digest...</div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="digest-container">
        <div className="digest-header">
          <div className="digest-title">Daily Digest</div>
          <div className="digest-subtitle">No digest items yet. Check back later.</div>
        </div>
      </div>
    )
  }

  return (
    <div className="digest-container">
      <div className="digest-header">
        <div className="digest-title">Daily Digest</div>
        <div className="digest-subtitle">Top {items.length} stories for today</div>
      </div>
      {items.map((item, idx) => (
        <div key={item.id || idx} className="digest-item">
          <div className="digest-rank">{idx + 1}</div>
          <div className="digest-item-content">
            <div className="digest-item-title">
              <a href={item.url} onClick={(e) => {
                e.preventDefault()
                if (openViewer) openViewer(item.url, item.title, item)
              }}>{item.title || 'Untitled'}</a>
            </div>
            <div className="digest-item-meta">
              {item.source_name && <span>{item.source_name}</span>}
              {item.score !== undefined && <span>{item.score} pts</span>}
              {item.published_at && <span>{formatTime(item.published_at)}</span>}
            </div>
          </div>
          {item.image_url && (
            <img className="digest-item-image" src={item.image_url} alt=""
              onError={e => { e.target.style.display = 'none' }} />
          )}
        </div>
      ))}
    </div>
  )
}
