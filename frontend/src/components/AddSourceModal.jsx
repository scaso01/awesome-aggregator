import React, { useState, useEffect } from 'react'

import SourcePreview from './SourcePreview'

const API_BASE = '/api'

const DISPLAY_FORMATS = {
  compact:   { label: 'Compact',   desc: 'Thumbnail + title side by side' },
  magazine:  { label: 'Magazine',  desc: 'Large image on top, text below' },
  headlines: { label: 'Headlines', desc: 'Titles only, ultra-dense' },
  cards:     { label: 'Cards',     desc: 'Card per item with image + text' },
  gallery:   { label: 'Gallery',   desc: 'Image grid, minimal text' },
  text_only: { label: 'Text Only', desc: 'Full text, no images' },
}

export default function AddSourceModal({ onAdd, onBatchAdd, onClose }) {
  const [tab, setTab] = useState('browse')
  const [suggestions, setSuggestions] = useState([])
  const [categories, setCategories] = useState([])
  const [activeCategory, setActiveCategory] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [adding, setAdding] = useState(null)
  const [selectedFormat, setSelectedFormat] = useState('compact')

  const [bundles, setBundles] = useState([])
  const [addingBundle, setAddingBundle] = useState(null)

  // Custom form state
  const [name, setName] = useState('')
  const [sourceType, setSourceType] = useState('rss')
  const [url, setUrl] = useState('')
  const [refreshSeconds, setRefreshSeconds] = useState(300)
  const [customFormat, setCustomFormat] = useState('compact')
  const [previewUrl, setPreviewUrl] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/discover/categories`).then(r => r.json()).then(setCategories).catch(() => {})
    fetch(`${API_BASE}/discover/suggestions`).then(r => r.json()).then(setSuggestions).catch(() => {})
    fetch(`${API_BASE}/discover/bundles`).then(r => r.json()).then(setBundles).catch(() => {})
  }, [])

  const filteredSuggestions = activeCategory
    ? suggestions.filter(s => s.category === activeCategory)
    : suggestions

  const handleSearch = async () => {
    if (searchQuery.length < 2) return
    setSearching(true)
    try {
      const res = await fetch(`${API_BASE}/discover/search?q=${encodeURIComponent(searchQuery)}`)
      setSearchResults(await res.json())
    } catch (err) { console.error('Search failed:', err) }
    finally { setSearching(false) }
  }

  const handleBundleAdd = async (bundle) => {
    if (!onBatchAdd) return
    setAddingBundle(bundle.id)
    await onBatchAdd(bundle.sources)
    setAddingBundle(null)
  }

  const quickAdd = async (source) => {
    setAdding(source.name)
    await onAdd({
      name: source.name,
      source_type: source.type,
      url: source.url,
      refresh_seconds: 300,
      display_format: selectedFormat,
    })
    setAdding(null)
  }

  const handleCustomSubmit = (e) => {
    e.preventDefault()
    if (!name || !url) return
    onAdd({ name, source_type: sourceType, url, refresh_seconds: refreshSeconds, display_format: customFormat })
  }

  const renderSourceCard = (source, idx) => (
    <div key={idx} className="source-card">
      <div className="source-card-info">
        <span className="source-card-icon">{source.icon}</span>
        <div>
          <div className="source-card-name">{source.name}</div>
          <div className="source-card-desc">{source.description}</div>
        </div>
      </div>
      <button className="btn btn-primary btn-sm" onClick={() => quickAdd(source)}
        disabled={adding === source.name}>
        {adding === source.name ? '...' : '+ Add'}
      </button>
    </div>
  )

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Sources</h2>
          <button className="btn btn-close" onClick={onClose}>&times;</button>
        </div>

        <div className="tab-bar">
          <button className={`tab ${tab === 'browse' ? 'active' : ''}`} onClick={() => setTab('browse')}>Browse</button>
          <button className={`tab ${tab === 'search' ? 'active' : ''}`} onClick={() => setTab('search')}>Search</button>
          <button className={`tab ${tab === 'custom' ? 'active' : ''}`} onClick={() => setTab('custom')}>Custom URL</button>
        </div>

        <div className="modal-body">
          {/* Format picker for browse/search tabs */}
          {(tab === 'browse' || tab === 'search') && (
            <div className="format-select-row">
              <label>Display as:</label>
              <select value={selectedFormat} onChange={e => setSelectedFormat(e.target.value)}>
                {Object.entries(DISPLAY_FORMATS).map(([key, { label }]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          )}

          {tab === 'browse' && (
            <>
              {bundles.length > 0 && (
                <div className="bundle-section">
                  <div className="bundle-section-title">Quick Start Bundles</div>
                  <div className="bundle-grid">
                    {bundles.map(bundle => (
                      <div key={bundle.id} className="bundle-card">
                        <div className="bundle-card-header">
                          <span className="bundle-card-emoji">{bundle.emoji}</span>
                          <span className="bundle-card-name">{bundle.name}</span>
                        </div>
                        <div className="bundle-card-desc">{bundle.description}</div>
                        <div className="bundle-card-footer">
                          <span className="bundle-card-count">{bundle.source_count} sources</span>
                          <button className="btn btn-primary btn-sm"
                            onClick={() => handleBundleAdd(bundle)}
                            disabled={addingBundle === bundle.id}>
                            {addingBundle === bundle.id ? '...' : 'Add All'}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="category-chips">
                <button className={`chip ${!activeCategory ? 'active' : ''}`}
                  onClick={() => setActiveCategory(null)}>All ({suggestions.length})</button>
                {categories.map(cat => (
                  <button key={cat.name}
                    className={`chip ${activeCategory === cat.name ? 'active' : ''}`}
                    onClick={() => setActiveCategory(cat.name)}>
                    {cat.name} ({cat.count})
                  </button>
                ))}
              </div>
              <div className="source-list">{filteredSuggestions.map(renderSourceCard)}</div>
            </>
          )}

          {tab === 'search' && (
            <>
              <div className="search-bar">
                <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  placeholder="Search sources... (e.g. 'python', 'r/gaming', 'nasa')" autoFocus />
                <button className="btn btn-primary" onClick={handleSearch} disabled={searching}>
                  {searching ? '...' : 'Search'}
                </button>
              </div>
              <div className="source-list">
                {searchResults.length === 0 && !searching && searchQuery && (
                  <div className="empty-search">No results. Try a different search or add a custom URL.</div>
                )}
                {searchResults.map(renderSourceCard)}
              </div>
            </>
          )}

          {tab === 'custom' && (
            <form onSubmit={handleCustomSubmit} className="custom-form">
              <div className="form-group">
                <label>Name</label>
                <input type="text" value={name} onChange={e => setName(e.target.value)}
                  placeholder="My Feed" required />
              </div>
              <div className="form-group">
                <label>Source Type</label>
                <select value={sourceType} onChange={e => setSourceType(e.target.value)}>
                  <option value="rss">RSS / Atom Feed</option>
                  <option value="youtube">YouTube Channel</option>
                  <option value="reddit">Reddit Subreddit</option>
                  <option value="generic">Any Website</option>
                </select>
              </div>
              <div className="form-group">
                <label>URL</label>
                <input type="url" value={url} onChange={e => setUrl(e.target.value)}
                  placeholder="https://..." required />
              </div>
              <div className="form-group">
                <label>Display Format</label>
                <select value={customFormat} onChange={e => setCustomFormat(e.target.value)}>
                  {Object.entries(DISPLAY_FORMATS).map(([key, { label, desc }]) => (
                    <option key={key} value={key}>{label} -- {desc}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Refresh Interval</label>
                <select value={refreshSeconds} onChange={e => setRefreshSeconds(Number(e.target.value))}>
                  <option value={60}>Every minute</option>
                  <option value={120}>Every 2 minutes</option>
                  <option value={300}>Every 5 minutes</option>
                  <option value={600}>Every 10 minutes</option>
                  <option value={1800}>Every 30 minutes</option>
                  <option value={3600}>Every hour</option>
                </select>
              </div>
              <div className="modal-actions">
                {/* Detect the type and show sample items before subscribing.
                    SourcePreview was written for exactly this and then wired to
                    nothing, so "paste any URL to auto-detect" was a README
                    claim with no button behind it. */}
                <button type="button" className="btn" disabled={!url}
                  onClick={() => setPreviewUrl(url)}>
                  Preview
                </button>
                <button type="submit" className="btn btn-primary">Add Source</button>
              </div>
            </form>
          )}
        </div>
      </div>

      {previewUrl && (
        <SourcePreview
          url={previewUrl}
          onClose={() => setPreviewUrl(null)}
          onAdd={(detected) => {
            setPreviewUrl(null)
            onAdd({ ...detected, display_format: customFormat })
          }}
        />
      )}
    </div>
  )
}
