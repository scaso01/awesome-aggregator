import React, { useState, useEffect } from 'react'

const API_BASE = '/api'

const EMOJI_OPTIONS = [
  '📰', '💼', '🎮', '🎬', '🎵', '📚', '🔬', '💻', '🏀', '⚽',
  '🌍', '🏠', '🍔', '✈️', '💰', '🎨', '🔧', '📱', '🎯', '⭐',
]

export default function ViewEditor({ view, sources, onSave, onClose }) {
  const [name, setName] = useState(view?.name || '')
  const [icon, setIcon] = useState(view?.icon || '')
  const [selectedSourceIds, setSelectedSourceIds] = useState(
    view?.source_ids ? new Set(view.source_ids) : new Set()
  )
  const [includeKeywords, setIncludeKeywords] = useState(view?.include_keywords || [])
  const [excludeKeywords, setExcludeKeywords] = useState(view?.exclude_keywords || [])
  const [includeInput, setIncludeInput] = useState('')
  const [excludeInput, setExcludeInput] = useState('')
  const [saving, setSaving] = useState(false)

  const toggleSource = (sourceId) => {
    setSelectedSourceIds(prev => {
      const next = new Set(prev)
      if (next.has(sourceId)) next.delete(sourceId)
      else next.add(sourceId)
      return next
    })
  }

  const addIncludeKeyword = () => {
    const kw = includeInput.trim()
    if (kw && !includeKeywords.includes(kw)) {
      setIncludeKeywords(prev => [...prev, kw])
    }
    setIncludeInput('')
  }

  const addExcludeKeyword = () => {
    const kw = excludeInput.trim()
    if (kw && !excludeKeywords.includes(kw)) {
      setExcludeKeywords(prev => [...prev, kw])
    }
    setExcludeInput('')
  }

  const handleSave = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      const payload = {
        name: name.trim(),
        icon,
        source_ids: Array.from(selectedSourceIds),
        include_keywords: includeKeywords,
        exclude_keywords: excludeKeywords,
      }
      if (view?.id) {
        await fetch(`${API_BASE}/views/${view.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } else {
        await fetch(`${API_BASE}/views/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      }
      if (onSave) onSave()
    } catch (err) { console.error('Failed to save view:', err) }
    finally { setSaving(false) }
  }

  return (
    <div className="view-editor-overlay" onClick={onClose}>
      <div className="view-editor" onClick={e => e.stopPropagation()}>
        <div className="view-editor-header">
          <h2 style={{ fontSize: '1.1rem', margin: 0 }}>
            {view?.id ? 'Edit View' : 'Create View'}
          </h2>
          <button className="btn btn-close" onClick={onClose}>&times;</button>
        </div>

        <div className="view-editor-body">
          <div className="form-group">
            <label>Name</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)}
              placeholder="e.g. Morning Briefing" />
          </div>

          <div className="form-group">
            <label>Icon</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
              {EMOJI_OPTIONS.map(emoji => (
                <button key={emoji}
                  style={{
                    fontSize: '1.2rem', padding: '4px 6px', cursor: 'pointer',
                    background: icon === emoji ? 'var(--accent-bright)' : 'var(--bg-card)',
                    border: icon === emoji ? '2px solid var(--accent-bright)' : '1px solid var(--border)',
                    borderRadius: '6px',
                  }}
                  onClick={() => setIcon(icon === emoji ? '' : emoji)}
                >{emoji}</button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Sources</label>
            <div style={{ maxHeight: '160px', overflowY: 'auto', marginTop: '4px' }}>
              {sources.map(source => (
                <label key={source.id} className="toggle-row" style={{ marginBottom: '4px' }}>
                  <input type="checkbox"
                    checked={selectedSourceIds.has(source.id)}
                    onChange={() => toggleSource(source.id)} />
                  <span>{source.name}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Include Keywords</label>
            <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
              <input type="text" value={includeInput}
                onChange={e => setIncludeInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addIncludeKeyword() } }}
                placeholder="Type and press Enter" style={{ flex: 1 }} />
            </div>
            <div className="keyword-chips">
              {includeKeywords.map(kw => (
                <span key={kw} className="keyword-chip">
                  {kw}
                  <span className="keyword-chip-remove"
                    onClick={() => setIncludeKeywords(prev => prev.filter(k => k !== kw))}>x</span>
                </span>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Exclude Keywords</label>
            <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
              <input type="text" value={excludeInput}
                onChange={e => setExcludeInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addExcludeKeyword() } }}
                placeholder="Type and press Enter" style={{ flex: 1 }} />
            </div>
            <div className="keyword-chips">
              {excludeKeywords.map(kw => (
                <span key={kw} className="keyword-chip">
                  {kw}
                  <span className="keyword-chip-remove"
                    onClick={() => setExcludeKeywords(prev => prev.filter(k => k !== kw))}>x</span>
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="view-editor-footer">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving || !name.trim()}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
