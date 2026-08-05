import React, { useState, useEffect } from 'react'

const API_BASE = '/api'

export default function SourcePreview({ url, onAdd, onClose }) {
  const [loading, setLoading] = useState(true)
  const [sourceInfo, setSourceInfo] = useState(null)
  const [previewItems, setPreviewItems] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const detect = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API_BASE}/detect/url`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url }),
        })
        if (!res.ok) throw new Error('Detection failed')
        const data = await res.json()
        if (!cancelled) {
          setSourceInfo(data.source || data)
          setPreviewItems(data.preview_items || [])
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to detect source')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    detect()
    return () => { cancelled = true }
  }, [url])

  const handleAdd = () => {
    if (sourceInfo && onAdd) {
      onAdd({
        name: sourceInfo.name || sourceInfo.title || url,
        source_type: sourceInfo.type || sourceInfo.source_type || 'rss',
        url: sourceInfo.feed_url || url,
        refresh_seconds: 300,
        display_format: 'compact',
      })
    }
  }

  return (
    <div className="source-preview-overlay" onClick={onClose}>
      <div className="source-preview" onClick={e => e.stopPropagation()}>
        <div className="source-preview-header">
          <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Source Preview</h2>
          <button className="btn btn-close" onClick={onClose}>&times;</button>
        </div>
        <div className="source-preview-body">
          {loading && <div className="loading">Detecting source...</div>}
          {error && <div className="error-text" style={{ padding: '16px' }}>{error}</div>}
          {!loading && !error && sourceInfo && (
            <>
              <div className="source-preview-type">
                {sourceInfo.type || sourceInfo.source_type || 'unknown'}
              </div>
              <h3 style={{ fontSize: '1rem', marginBottom: '12px', color: 'var(--text-primary)' }}>
                {sourceInfo.name || sourceInfo.title || url}
              </h3>
              {previewItems.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                    Preview ({previewItems.length} items)
                  </div>
                  {previewItems.slice(0, 3).map((item, idx) => (
                    <div key={idx} className="source-preview-item">
                      <div style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                        {item.title || 'Untitled'}
                      </div>
                      {item.published_at && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {new Date(item.published_at).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
        <div className="source-preview-footer">
          <button className="btn" onClick={onClose}>Close</button>
          {sourceInfo && (
            <button className="btn btn-primary" onClick={handleAdd}>Add</button>
          )}
        </div>
      </div>
    </div>
  )
}
