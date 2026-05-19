'use client'

import { useState, useEffect } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import appConfig from '../../config'

export default function NewsPage() {
  const [news, setNews] = useState({ events: [], blackout_active: false })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchNews()
    const interval = setInterval(fetchNews, 60000)
    return () => clearInterval(interval)
  }, [])

  const fetchNews = async () => {
    const res = await fetch(`${appConfig.API_URL}/news`)
    if (res.ok) setNews(await res.json())
  }

  const refreshNews = async () => {
    setLoading(true)
    await fetch(`${appConfig.API_URL}/news/refresh`, { method: 'POST' })
    await fetchNews()
    setLoading(false)
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">News Calendar</h1>
          <p className="text-gray-400">Economic events affecting EUR/USD</p>
        </div>
        <button onClick={refreshNews} disabled={loading} className="flex items-center gap-2 px-4 py-2 bg-forex-blue rounded-lg hover:bg-blue-600 disabled:opacity-50">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Blackout Warning */}
      {news.blackout_active && (
        <div className="mb-6 p-4 bg-yellow-500/20 border border-yellow-500/50 rounded-xl flex items-center gap-3">
          <AlertTriangle className="text-yellow-400" size={24} />
          <div>
            <p className="font-medium text-yellow-400">Trading Blackout Active</p>
            <p className="text-sm text-gray-300">{news.blackout_reason}</p>
          </div>
        </div>
      )}

      {/* Next High Impact */}
      {news.next_high_impact && (
        <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-xl">
          <p className="text-sm text-gray-400">Next High Impact Event</p>
          <p className="font-medium">{news.next_high_impact.title}</p>
          <p className="text-sm text-gray-400">
            {news.next_high_impact.currency} - {new Date(news.next_high_impact.time).toLocaleString()}
            ({Math.round(news.next_high_impact.minutes_until)} min)
          </p>
        </div>
      )}

      {/* Events List */}
      <div className="bg-forex-card rounded-xl border border-forex-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-gray-400 text-sm bg-gray-800/50">
                <th className="text-left py-3 px-4">Impact</th>
                <th className="text-left py-3 px-4">Time</th>
                <th className="text-left py-3 px-4">Currency</th>
                <th className="text-left py-3 px-4">Event</th>
                <th className="text-left py-3 px-4">Forecast</th>
                <th className="text-left py-3 px-4">Previous</th>
                <th className="text-left py-3 px-4">Countdown</th>
              </tr>
            </thead>
            <tbody>
              {news.events?.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-gray-400">
                    No upcoming events
                  </td>
                </tr>
              ) : (
                news.events?.map((event, i) => (
                  <tr key={i} className="border-t border-forex-border/50 hover:bg-gray-800/30">
                    <td className="py-3 px-4">
                      <ImpactBadge impact={event.impact} />
                    </td>
                    <td className="py-3 px-4 text-sm">
                      {new Date(event.time).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-medium">{event.currency}</td>
                    <td className="py-3 px-4">{event.title}</td>
                    <td className="py-3 px-4 text-gray-400">{event.forecast || '-'}</td>
                    <td className="py-3 px-4 text-gray-400">{event.previous || '-'}</td>
                    <td className="py-3 px-4">
                      <Countdown minutes={event.minutes_until} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function ImpactBadge({ impact }) {
  const styles = {
    HIGH: 'bg-red-500/20 text-red-400',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400',
    LOW: 'bg-gray-500/20 text-gray-400'
  }

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${styles[impact] || styles.LOW}`}>
      {impact}
    </span>
  )
}

function Countdown({ minutes }) {
  if (minutes < 0) return <span className="text-gray-400">Past</span>
  if (minutes < 60) return <span className="text-forex-red font-medium">{Math.round(minutes)}m</span>
  if (minutes < 1440) return <span className="text-forex-yellow">{Math.round(minutes / 60)}h</span>
  return <span className="text-gray-400">{Math.round(minutes / 1440)}d</span>
}
