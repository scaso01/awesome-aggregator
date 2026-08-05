import React, { useState, useEffect, useRef } from 'react'

import ItemActionMenu from './ItemActionMenu'

export const DISPLAY_FORMATS = {
  compact:   { label: 'Compact',   desc: 'Thumbnail + title side by side' },
  magazine:  { label: 'Magazine',  desc: 'Large image on top, text below' },
  headlines: { label: 'Headlines', desc: 'Titles only, ultra-dense' },
  cards:     { label: 'Cards',     desc: 'Card per item with image + text' },
  gallery:   { label: 'Gallery',   desc: 'Image grid, minimal text' },
  text_only: { label: 'Text Only', desc: 'Full text, no images' },
}

export default function ContentPanel({ source, items, onHide, onUpdateSource, openViewer, formatTime, onHideItem, onMuteSource }) {
  const [showFormatMenu, setShowFormatMenu] = useState(false)
  const [showCustomBuilder, setShowCustomBuilder] = useState(false)
  const [customShow, setCustomShow] = useState(source.custom_style?.show || {
    image: true, description: true, author: true, date: true, score: true, domain: true,
  })
  const [customImageSize, setCustomImageSize] = useState(source.custom_style?.imageSize || 'medium')
  const [customImagePos, setCustomImagePos] = useState(source.custom_style?.imagePos || 'left')
  const [customFontSize, setCustomFontSize] = useState(source.custom_style?.fontSize || '0.85rem')
  const [customDescLines, setCustomDescLines] = useState(source.custom_style?.descLines || 2)
  const menuRef = useRef(null)
  const fmt = source.display_format || 'compact'
  const style = source.custom_style || {}
  const typeIcons = { rss: 'RSS', youtube: 'YT', reddit: 'R', generic: 'Web' }

  // Close menu on outside click
  useEffect(() => {
    if (!showFormatMenu) return
    const handler = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setShowFormatMenu(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showFormatMenu])

  const pickFormat = (key) => {
    setShowFormatMenu(false)
    setShowCustomBuilder(false)
    onUpdateSource({ display_format: key }, null)
  }

  const applyCustom = () => {
    const customStyle = { isCustom: true, show: customShow, imageSize: customImageSize, imagePos: customImagePos, fontSize: customFontSize, descLines: customDescLines }
    onUpdateSource({ display_format: 'compact' }, customStyle)
    setShowFormatMenu(false)
    setShowCustomBuilder(false)
  }

  // Helper: clickable link that opens in-app viewer
  const Link = ({ url, title, item, children, className, style: linkStyle }) => (
    <a href={url} className={className} style={linkStyle} onClick={(e) => {
      e.preventDefault(); openViewer(url, title || '', item)
    }}>{children}</a>
  )

  const renderItem = (item, idx) => {
    const key = item.id || idx

    // Headlines — title only
    if (fmt === 'headlines') {
      return (
        <div key={key} className="content-item fmt-headlines">
          <Link url={item.url} title={item.title} item={item}>{item.title || 'Untitled'}</Link>
          <span className="item-meta-inline">{formatTime(item.published_at)}</span>
        </div>
      )
    }

    // Gallery — image grid
    if (fmt === 'gallery') {
      return (
        <Link key={key} className="gallery-item" url={item.url} title={item.title} item={item}>
          {item.image_url ? (
            <img src={item.image_url} alt="" loading="lazy" onError={e => { e.target.src = '' ; e.target.style.display = 'none' }} />
          ) : (
            <div className="gallery-placeholder">{(item.title || '?').substring(0, 40)}</div>
          )}
        </Link>
      )
    }

    // Magazine — large image top, text below
    if (fmt === 'magazine') {
      return (
        <div key={key} className="content-item fmt-magazine">
          {item.image_url && (
            <Link url={item.url} title={item.title} item={item}>
              <img className="magazine-img" src={item.image_url} alt="" loading="lazy"
                onError={e => { e.target.style.display = 'none' }} />
            </Link>
          )}
          <div className="magazine-text">
            <div className="item-title">
              <Link url={item.url} title={item.title} item={item}>{item.title || 'Untitled'}</Link>
            </div>
            <div className="item-meta">
              {item.author && <span>{item.author}</span>}
              {item.published_at && <span>{formatTime(item.published_at)}</span>}
              {item.metadata?.score !== undefined && <span>{item.metadata.score} pts</span>}
            </div>
            {item.description && item.description !== item.title && (
              <div className="item-description">{item.description.substring(0, 300)}</div>
            )}
          </div>
        </div>
      )
    }

    // Cards — bordered card with image + full text
    if (fmt === 'cards') {
      return (
        <div key={key} className="content-item fmt-card">
          {item.image_url && (
            <Link url={item.url} title={item.title} item={item}>
              <img className="card-img" src={item.image_url} alt="" loading="lazy"
                onError={e => { e.target.style.display = 'none' }} />
            </Link>
          )}
          <div className="card-body">
            <div className="item-title">
              <Link url={item.url} title={item.title} item={item}>{item.title || 'Untitled'}</Link>
            </div>
            <div className="item-meta">
              {item.author && <span>{item.author}</span>}
              {item.published_at && <span>{formatTime(item.published_at)}</span>}
              {item.metadata?.domain && <span className="item-domain">{item.metadata.domain}</span>}
            </div>
            {item.description && item.description !== item.title && (
              <div className="item-description">{item.description.substring(0, 200)}</div>
            )}
          </div>
        </div>
      )
    }

    // Text Only — no images ever
    if (fmt === 'text_only') {
      return (
        <div key={key} className="content-item fmt-text">
          <div className="item-title">
            <Link url={item.url} title={item.title} item={item}>{item.title || 'Untitled'}</Link>
          </div>
          <div className="item-meta">
            {item.author && <span>{item.author}</span>}
            {item.published_at && <span>{formatTime(item.published_at)}</span>}
            {item.metadata?.score !== undefined && <span>{item.metadata.score} pts</span>}
            {item.metadata?.num_comments !== undefined && <span>{item.metadata.num_comments} comments</span>}
          </div>
          {item.description && item.description !== item.title && (
            <div className="item-description">{item.description.substring(0, 400)}</div>
          )}
        </div>
      )
    }

    // Custom format — user-configured elements
    if (style.isCustom) {
      const show = style.show || {}
      const imgSize = style.imageSize || 'medium'
      const imgPos = style.imagePos || 'left'
      const lines = style.descLines ?? 2
      const showImg = show.image !== false && item.image_url
      const isTop = imgPos === 'top' || imgSize === 'large'
      const imgW = imgSize === 'small' ? '60px' : imgSize === 'medium' ? '120px' : '100%'
      const imgH = imgSize === 'small' ? '45px' : imgSize === 'medium' ? '90px' : '180px'

      return (
        <div key={key} className={`content-item ${showImg && !isTop ? 'has-image' : ''}`}
          style={isTop ? {} : undefined}>
          {showImg && isTop && (
            <Link url={item.url} title={item.title} item={item}>
              <img src={item.image_url} alt="" loading="lazy" style={{ width: '100%', maxHeight: imgH, objectFit: 'cover', display: 'block' }}
                onError={e => { e.target.style.display = 'none' }} />
            </Link>
          )}
          <div style={showImg && !isTop ? { display: 'flex', gap: '10px', flexDirection: imgPos === 'right' ? 'row-reverse' : 'row' } : {}}>
            {showImg && !isTop && (
              <div style={{ flexShrink: 0, width: imgW, height: imgH, borderRadius: '4px', overflow: 'hidden' }}>
                <Link url={item.url} title={item.title} item={item}>
                  <img src={item.image_url} alt="" loading="lazy" style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    onError={e => { e.target.style.display = 'none' }} />
                </Link>
              </div>
            )}
            <div style={{ flex: 1, minWidth: 0, padding: isTop && showImg ? '8px 12px' : undefined }}>
              <div className="item-title">
                <Link url={item.url} title={item.title} item={item}>{item.title || 'Untitled'}</Link>
              </div>
              <div className="item-meta">
                {show.author !== false && item.author && <span>{item.author}</span>}
                {show.date !== false && item.published_at && <span>{formatTime(item.published_at)}</span>}
                {show.score !== false && item.metadata?.score !== undefined && <span>{item.metadata.score} pts</span>}
                {show.domain !== false && item.metadata?.domain && <span className="item-domain">{item.metadata.domain}</span>}
              </div>
              {show.description !== false && lines > 0 && item.description && item.description !== item.title && (
                <div className="item-description" style={lines < 99 ? { WebkitLineClamp: lines } : { WebkitLineClamp: 'unset' }}>
                  {item.description.substring(0, lines >= 99 ? 1000 : lines * 120)}
                </div>
              )}
            </div>
          </div>
        </div>
      )
    }

    // Compact (default) — thumbnail + text side by side
    return (
      <div key={key} className={`content-item ${item.image_url ? 'has-image' : ''}`}>
        {item.image_url && (
          <div className="item-image-wrap">
            <Link url={item.url} title={item.title} item={item}>
              <img src={item.image_url} alt="" loading="lazy"
                onError={e => { e.target.style.display = 'none' }} />
            </Link>
          </div>
        )}
        <div className="item-content">
          <div className="item-title">
            <Link url={item.url} title={item.title} item={item}>{item.title || 'Untitled'}</Link>
          </div>
          <div className="item-meta">
            {item.author && <span>{item.author}</span>}
            {item.published_at && <span>{formatTime(item.published_at)}</span>}
            {item.metadata?.score !== undefined && <span>{item.metadata.score} pts</span>}
            {item.metadata?.num_comments !== undefined && <span>{item.metadata.num_comments} comments</span>}
            {item.metadata?.domain && <span className="item-domain">{item.metadata.domain}</span>}
            {item.metadata?.link_flair && <span className="item-flair">{item.metadata.link_flair}</span>}
          </div>
          {item.description && item.description !== item.title && (
            <div className="item-description">
              {item.description.length > 200 ? item.description.substring(0, 200) + '...' : item.description}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Attach the bookmark/hide/mute menu to every item, in every display format.
  //
  // ItemActionMenu was written, styled and imported by nothing, so the three dot
  // menu the README describes did not exist on screen at all. Injecting it here
  // rather than inside each of the six format branches keeps the formats from
  // drifting apart again. Gallery renders a link rather than a host element and
  // has no room for it, so it is left alone.
  const renderItemWithActions = (item, idx) => {
    const el = renderItem(item, idx)
    if (!el || typeof el.type !== 'string') return el
    return React.cloneElement(el, {}, (
      <>
        <ItemActionMenu
          item={item}
          onHideItem={onHideItem}
          onMuteSource={onMuteSource}
        />
        {el.props.children}
      </>
    ))
  }

  return (
    <div className="content-panel">
      <div className="panel-header">
        <div className="panel-drag-handle">
          <span className={`status-dot status-${source.status}`} />
          <span className="panel-title">{source.name}</span>
          <span className="panel-badge">{typeIcons[source.source_type] || '?'}</span>
          <span className="panel-count">{source.item_count || items.length}</span>
        </div>
        <div className="panel-controls" onMouseDown={e => e.stopPropagation()}>
          <div className="format-picker-wrap" ref={menuRef}>
            <button className="btn btn-icon" onClick={() => setShowFormatMenu(!showFormatMenu)}
              title="Change display format">&#9881;</button>
            {showFormatMenu && (
              <div className="format-menu">
                <div className="format-menu-title">Display Format</div>
                {Object.entries(DISPLAY_FORMATS).map(([key, { label, desc }]) => (
                  <button key={key} className={`format-option ${fmt === key && !style.isCustom ? 'active' : ''}`}
                    onClick={() => pickFormat(key)}>
                    <span className="format-label">{label}</span>
                    <span className="format-desc">{desc}</span>
                  </button>
                ))}
                <div className="format-divider" />
                <button className={`format-option ${style.isCustom ? 'active' : ''}`}
                  onClick={() => setShowCustomBuilder(!showCustomBuilder)}>
                  <span className="format-label">Custom</span>
                  <span className="format-desc">Build your own layout</span>
                </button>
                {showCustomBuilder && (
                  <div className="custom-builder">
                    <div className="settings-section">
                      <label className="settings-label">Show Elements</label>
                      <div className="settings-toggles">
                        {[['image','Images'],['description','Description'],['author','Author'],['date','Date'],['score','Score'],['domain','Domain']].map(([k,l]) => (
                          <label key={k} className="toggle-row">
                            <input type="checkbox" checked={customShow[k] !== false}
                              onChange={() => setCustomShow(prev => ({ ...prev, [k]: !prev[k] }))} />
                            <span>{l}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                    {customShow.image !== false && (
                      <div className="settings-row">
                        <div className="settings-section" style={{ flex: 1 }}>
                          <label className="settings-label">Image Size</label>
                          <select value={customImageSize} onChange={e => setCustomImageSize(e.target.value)} className="settings-input">
                            <option value="small">Small</option>
                            <option value="medium">Medium</option>
                            <option value="large">Large</option>
                          </select>
                        </div>
                        <div className="settings-section" style={{ flex: 1 }}>
                          <label className="settings-label">Position</label>
                          <select value={customImagePos} onChange={e => setCustomImagePos(e.target.value)} className="settings-input">
                            <option value="left">Left</option>
                            <option value="right">Right</option>
                            <option value="top">Top</option>
                          </select>
                        </div>
                      </div>
                    )}
                    <div className="settings-row">
                      <div className="settings-section" style={{ flex: 1 }}>
                        <label className="settings-label">Font Size</label>
                        <select value={customFontSize} onChange={e => setCustomFontSize(e.target.value)} className="settings-input">
                          <option value="0.72rem">Small</option>
                          <option value="0.85rem">Medium</option>
                          <option value="1rem">Large</option>
                        </select>
                      </div>
                      <div className="settings-section" style={{ flex: 1 }}>
                        <label className="settings-label">Desc Lines</label>
                        <select value={customDescLines} onChange={e => setCustomDescLines(Number(e.target.value))} className="settings-input">
                          <option value={0}>None</option>
                          <option value={1}>1</option>
                          <option value={2}>2</option>
                          <option value={3}>3</option>
                          <option value={99}>Full</option>
                        </select>
                      </div>
                    </div>
                    <button className="btn btn-primary" style={{ width: '100%', marginTop: '6px' }}
                      onClick={applyCustom}>Apply Custom</button>
                  </div>
                )}
              </div>
            )}
          </div>
          <button className="btn btn-close" onClick={onHide} title="Hide panel">&times;</button>
        </div>
      </div>

      <div className={`panel-body ${fmt === 'gallery' ? 'panel-gallery' : ''}`}
        style={style.fontSize ? { fontSize: style.fontSize } : undefined}>
        {items.length === 0 ? (
          <div className="loading" style={{ padding: '20px' }}>
            {source.status === 'error' ? (
              <span className="error-text">Error: {source.last_error || 'Failed to fetch'}</span>
            ) : 'Loading...'}
          </div>
        ) : (
          items.map(renderItemWithActions)
        )}
      </div>
    </div>
  )
}
