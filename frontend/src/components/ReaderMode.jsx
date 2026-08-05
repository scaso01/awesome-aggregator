import React, { useState, useEffect, useRef } from 'react'

const API_BASE = '/api'

export default function ReaderMode({ url, title, item = null, onClose }) {
  const [loading, setLoading] = useState(true)
  const [article, setArticle] = useState(null)
  const [fallbackToIframe, setFallbackToIframe] = useState(false)
  const [fontSize, setFontSize] = useState(1.1)
  const [bookmarked, setBookmarked] = useState(false)
  const iframeRef = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  useEffect(() => {
    let cancelled = false
    const fetchArticle = async () => {
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE}/reader/extract?url=${encodeURIComponent(url)}`)
        if (!res.ok) throw new Error('Extraction failed')
        const data = await res.json()
        if (!cancelled) {
          // The endpoint returns content_html. Branching on data.content meant
          // this was never once true, so reader mode silently fell through to
          // the iframe every single time and the extracted article view, which
          // is the whole point of the feature, was dead code.
          if (data.content_html) {
            setArticle(data)
          } else {
            setFallbackToIframe(true)
          }
        }
      } catch {
        if (!cancelled) setFallbackToIframe(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchArticle()
    return () => { cancelled = true }
  }, [url])

  // POST /api/bookmarks/, not /api/actions/bookmark, which has never existed.
  // A bookmark is keyed on the content item, so this is only offered when the
  // reader was opened from one.
  const handleBookmark = async () => {
    if (!item) return
    try {
      const res = await fetch(`${API_BASE}/bookmarks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content_item_id: item.id,
          source_id: item.source_id,
          title: item.title || title,
          url: item.url || url,
          image_url: item.image_url || null,
        }),
      })
      if (!res.ok) throw new Error(`Bookmark failed: ${res.status}`)
      setBookmarked(true)
    } catch (err) { console.error('Bookmark failed:', err) }
  }

  const decreaseFontSize = () => setFontSize(prev => Math.max(0.8, prev - 0.1))
  const increaseFontSize = () => setFontSize(prev => Math.min(1.6, prev + 0.1))

  // Loading skeleton
  if (loading) {
    return (
      <div className="reader-overlay">
        <div className="reader-header">
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Loading...</span>
          <div className="reader-actions">
            <button className="btn btn-close" onClick={onClose}>&times;</button>
          </div>
        </div>
        <div className="reader-body">
          <div className="reader-content reader-skeleton">
            <div className="reader-skeleton-title" />
            <div className="reader-skeleton-meta" />
            <div className="reader-skeleton-line" />
            <div className="reader-skeleton-line" />
            <div className="reader-skeleton-line" />
            <div className="reader-skeleton-line" />
            <div className="reader-skeleton-line" />
            <div className="reader-skeleton-line" />
          </div>
        </div>
      </div>
    )
  }

  // Fallback to iframe
  if (fallbackToIframe) {
    return (
      <div className="reader-overlay">
        <div className="reader-header">
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
            {title || url}
          </span>
          <div className="reader-actions">
            <a href={url} target="_blank" rel="noopener noreferrer" className="btn btn-sm">Open in browser</a>
            <button className="btn btn-close" onClick={onClose}>&times;</button>
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <iframe
            ref={iframeRef}
            src={url}
            title={title || 'Article'}
            style={{ width: '100%', height: '100%', border: 'none', background: 'white' }}
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          />
        </div>
      </div>
    )
  }

  // Reader mode view
  return (
    <div className="reader-overlay">
      <div className="reader-header">
        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
          {article?.site_name || title || url}
        </span>
        <div className="reader-actions">
          <div className="reader-font-controls">
            <button className="reader-font-btn" onClick={decreaseFontSize}>A-</button>
            <button className="reader-font-btn" onClick={increaseFontSize}>A+</button>
          </div>
          {item && (
            <button className="btn btn-sm" onClick={handleBookmark} disabled={bookmarked}>
              {bookmarked ? 'Bookmarked' : 'Bookmark'}
            </button>
          )}
          <a href={url} target="_blank" rel="noopener noreferrer" className="btn btn-sm">Open in browser</a>
          <button className="btn btn-close" onClick={onClose}>&times;</button>
        </div>
      </div>
      <div className="reader-body">
        <div className="reader-content">
          {/* The extractor returns the literal string "Untitled" when it cannot
              find a heading, and that is truthy, so it used to beat the good
              title we already have from the feed. */}
          <h1 className="reader-title">
            {article?.title && article.title !== 'Untitled' ? article.title : (title || 'Untitled')}
          </h1>
          <div className="reader-meta">
            {article?.author && <span>By {article.author}</span>}
            {article?.date && <span>{article.date}</span>}
            {article?.estimated_read_minutes &&
              <span>{article.estimated_read_minutes} min read</span>}
            {article?.site_name && <span>{article.site_name}</span>}
          </div>
          {article?.hero_image && (
            <img className="reader-hero-image" src={article.hero_image} alt=""
              onError={e => { e.target.style.display = 'none' }} />
          )}
          <div className="reader-article" style={{ fontSize: `${fontSize}rem` }}
            dangerouslySetInnerHTML={{ __html: article?.content_html || '' }} />
        </div>
      </div>
    </div>
  )
}
