import React, { useState, useEffect } from 'react'

const API_BASE = '/api'

export default function OnboardingPicker({ onComplete, onSkip }) {
  const [topics, setTopics] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/discover/onboarding/topics`)
      .then(r => r.json()).then(setTopics).catch(() => {})
  }, [])

  const toggle = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleGetStarted = async () => {
    if (selected.size === 0) return
    setLoading(true)
    try {
      const topicIds = Array.from(selected).join(',')
      const res = await fetch(`${API_BASE}/discover/onboarding/sources?topics=${topicIds}`)
      const sources = await res.json()
      if (sources.length > 0) await onComplete(sources)
    } catch (err) { console.error('Onboarding failed:', err) }
    finally { setLoading(false) }
  }

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-container">
        <h1 className="onboarding-heading">What interests you?</h1>
        <p className="onboarding-subtitle">Pick topics to build your personalized feed</p>

        <div className="onboarding-grid">
          {topics.map(topic => (
            <div key={topic.id}
              className={`onboarding-topic ${selected.has(topic.id) ? 'selected' : ''}`}
              onClick={() => toggle(topic.id)}>
              <span className="onboarding-topic-emoji">{topic.emoji}</span>
              <span className="onboarding-topic-name">{topic.name}</span>
              <span className="onboarding-topic-count">{topic.source_count} sources</span>
            </div>
          ))}
        </div>

        <div className="onboarding-footer">
          <span className="onboarding-footer-info">
            {selected.size > 0 ? `${selected.size} topic${selected.size > 1 ? 's' : ''} selected` : 'Select at least one topic'}
          </span>
          <button className="onboarding-cta" onClick={handleGetStarted}
            disabled={selected.size === 0 || loading}>
            {loading ? 'Setting up...' : 'Get Started'}
          </button>
          <button className="onboarding-skip" onClick={onSkip}>Skip, I'll add sources manually</button>
        </div>
      </div>
    </div>
  )
}
