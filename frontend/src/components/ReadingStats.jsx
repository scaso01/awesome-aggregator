import React, { useState, useEffect } from 'react'

const API_BASE = '/api'

export default function ReadingStats() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE}/stats/summary`)
        if (res.ok) {
          const data = await res.json()
          setStats(data)
        }
      } catch (err) { console.error('Failed to fetch stats:', err) }
    }
    fetchStats()
  }, [])

  if (!stats) return null

  // The endpoint returns today_count, week_count and a top_sources list. This
  // read articles_today, articles_week and a scalar top_source, none of which
  // exist, so the bar showed a hard zero no matter how much you had read.
  const topSource = stats.top_sources && stats.top_sources[0]

  return (
    <div className="reading-stats">
      <div className="reading-stats-item">
        Today: <span className="reading-stats-value">{stats.today_count ?? 0}</span>
      </div>
      <div className="reading-stats-item">
        This week: <span className="reading-stats-value">{stats.week_count ?? 0}</span>
      </div>
      {topSource && (
        <div className="reading-stats-item">
          Top: <span className="reading-stats-value">{topSource.name}</span>
        </div>
      )}
    </div>
  )
}
