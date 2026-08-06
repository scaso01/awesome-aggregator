import React, { useState } from 'react'

const API_BASE = '/api'

export default function TabBar({ views, activeViewId, onSelectView, onCreateView, onEditView, onReorderViews }) {
  const [dragOverId, setDragOverId] = useState(null)

  const handleDragStart = (e, viewId) => {
    e.dataTransfer.setData('text/plain', String(viewId))
  }

  const handleDragOver = (e, viewId) => {
    e.preventDefault()
    setDragOverId(viewId)
  }

  const handleDrop = (e, targetViewId) => {
    e.preventDefault()
    const sourceViewId = parseInt(e.dataTransfer.getData('text/plain'))
    if (sourceViewId !== targetViewId && onReorderViews) {
      // Reorder: move source before target
      const ids = views.map(v => v.id)
      const fromIdx = ids.indexOf(sourceViewId)
      const toIdx = ids.indexOf(targetViewId)
      ids.splice(fromIdx, 1)
      ids.splice(toIdx, 0, sourceViewId)
      onReorderViews(ids)
    }
    setDragOverId(null)
  }

  return (
    <div className="view-tab-bar">
      <button
        className={`view-tab ${activeViewId === null ? 'active' : ''}`}
        onClick={() => onSelectView(null)}
      >All</button>
      <button
        className={`view-tab ${activeViewId === 'bookmarks' ? 'active' : ''}`}
        onClick={() => onSelectView('bookmarks')}
      >Bookmarks</button>
      <button
        className={`view-tab ${activeViewId === 'digest' ? 'active' : ''}`}
        onClick={() => onSelectView('digest')}
      >Digest</button>
      {views.map(view => (
        <button
          key={view.id}
          className={`view-tab ${activeViewId === view.id ? 'active' : ''} ${dragOverId === view.id ? 'drag-over' : ''}`}
          onClick={() => onSelectView(view.id)}
          draggable
          onDragStart={e => handleDragStart(e, view.id)}
          onDragOver={e => handleDragOver(e, view.id)}
          onDrop={e => handleDrop(e, view.id)}
          onDragEnd={() => setDragOverId(null)}
        >
          {view.icon && <span className="view-tab-icon">{view.icon}</span>}
          {view.name}
          {/* ViewEditor has always had a full Edit View mode, and nothing
              could open it: the only caller set the view being edited to null,
              so a view could never be renamed, re-scoped or have its keywords
              changed once created. This is that mode's entry point. */}
          {activeViewId === view.id && onEditView && (
            <span
              className="view-tab-edit"
              role="button"
              title={`Edit ${view.name}`}
              onClick={e => { e.stopPropagation(); onEditView(view) }}
            >&#9998;</span>
          )}
        </button>
      ))}
      <button className="view-tab view-tab-add" onClick={onCreateView}>+</button>
    </div>
  )
}
