import React, { useState, useEffect } from 'react'

const API_BASE = '/api'

export default function MutedSources({ onClose }) {
  const [mutedSources, setMutedSources] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMuted()
  }, [])

  const fetchMuted = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/actions/muted`)
      if (res.ok) {
        const data = await res.json()
        setMutedSources(data)
      }
    } catch (err) { console.error('Failed to fetch muted sources:', err) }
    finally { setLoading(false) }
  }

  const handleUnmute = async (sourceId) => {
    try {
      await fetch(`${API_BASE}/actions/mute/${sourceId}`, { method: 'DELETE' })
      setMutedSources(prev => prev.filter(s => s.source_id !== sourceId))
    } catch (err) { console.error('Failed to unmute source:', err) }
  }

  const formatExpiry = (expiresAt) => {
    if (!expiresAt) return 'Permanent'
    const diff = new Date(expiresAt) - Date.now()
    if (diff <= 0) return 'Expired'
    const hours = Math.floor(diff / 3600000)
    if (hours < 24) return `${hours}h remaining`
    const days = Math.floor(hours / 24)
    return `${days}d remaining`
  }

  return (
    <div className="view-editor-overlay" onClick={onClose}>
      <div className="view-editor" onClick={e => e.stopPropagation()}>
        <div className="view-editor-header">
          <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Muted Sources</h2>
          <button className="btn btn-close" onClick={onClose}>&times;</button>
        </div>
        <div className="view-editor-body">
          {loading && <div className="loading">Loading...</div>}
          {!loading && mutedSources.length === 0 && (
            <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No muted sources.
            </div>
          )}
          {!loading && mutedSources.length > 0 && (
            <div className="muted-sources-list">
              {mutedSources.map(source => (
                <div key={source.source_id} className="muted-source-row">
                  <div className="muted-source-info">
                    {/* The endpoint returns source_name and mute_until. This
                        read name and expires_at, neither of which exists in
                        the response, so every row said "Source #12" and every
                        expiry read as Permanent however it was muted. */}
                    <span className="muted-source-name">{source.source_name || `Source #${source.source_id}`}</span>
                    <span className="muted-source-expiry">{formatExpiry(source.mute_until)}</span>
                  </div>
                  <button className="btn btn-sm" onClick={() => handleUnmute(source.source_id)}>Unmute</button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="view-editor-footer">
          <button className="btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
