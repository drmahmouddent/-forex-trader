'use client'

import { useState, useEffect } from 'react'
import { Activity, TrendingUp, TrendingDown, AlertTriangle, Play, Square, Zap } from 'lucide-react'
import config from '../config'

export default function Dashboard() {
  const [status, setStatus] = useState(null)
  const [positions, setPositions] = useState([])
  const [news, setNews] = useState({ events: [], blackout_active: false })
  const [risk, setRisk] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [statusRes, posRes, newsRes, riskRes] = await Promise.all([
        fetch(`${config.API_URL}/engine/status`),
        fetch(`${config.API_URL}/positions`),
        fetch(`${config.API_URL}/news`),
        fetch(`${config.API_URL}/risk`)
      ])

      if (statusRes.ok) setStatus(await statusRes.json())
      if (posRes.ok) setPositions(await posRes.json())
      if (newsRes.ok) setNews(await newsRes.json())
      if (riskRes.ok) setRisk(await riskRes.json())
    } catch (err) {
      console.error('Failed to fetch data:', err)
    } finally {
      setLoading(false)
    }
  }

  const startEngine = async () => {
    await fetch(`${config.API_URL}/engine/start`, { method: 'POST' })
    fetchData()
  }

  const stopEngine = async () => {
    await fetch(`${config.API_URL}/engine/stop`, { method: 'POST' })
    fetchData()
  }

  const emergencyStop = async () => {
    if (confirm('This will close ALL open positions. Continue?')) {
      await fetch(`${config.API_URL}/engine/emergency-stop`, { method: 'POST' })
      fetchData()
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-forex-blue"></div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Trading Dashboard</h1>
          <p className="text-gray-400">EUR/USD Automated Trading System</p>
        </div>
        <div className="flex gap-3">
          {status?.running ? (
            <button onClick={stopEngine} className="flex items-center gap-2 px-4 py-2 bg-forex-red rounded-lg hover:bg-red-600 transition">
              <Square size={16} /> Stop Bot
            </button>
          ) : (
            <button onClick={startEngine} className="flex items-center gap-2 px-4 py-2 bg-forex-green rounded-lg hover:bg-green-600 transition">
              <Play size={16} /> Start Bot
            </button>
          )}
          <button onClick={emergencyStop} className="flex items-center gap-2 px-4 py-2 bg-red-900 rounded-lg hover:bg-red-800 transition">
            <Zap size={16} /> Emergency Stop
          </button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatusCard
          title="Bot Status"
          value={status?.status || 'OFFLINE'}
          icon={<Activity size={20} />}
          color={status?.running ? 'green' : 'red'}
        />
        <StatusCard
          title="Account Balance"
          value={`$${status?.account?.balance?.toLocaleString() || '0'}`}
          icon={<TrendingUp size={20} />}
          color="blue"
        />
        <StatusCard
          title="Open Positions"
          value={positions.length}
          icon={<TrendingDown size={20} />}
          color="purple"
        />
        <StatusCard
          title="News Blackout"
          value={news.blackout_active ? 'ACTIVE' : 'Clear'}
          icon={<AlertTriangle size={20} />}
          color={news.blackout_active ? 'yellow' : 'green'}
          subtitle={news.blackout_reason}
        />
      </div>

      {/* Risk Summary */}
      {risk?.summary && (
        <div className="bg-forex-card rounded-xl border border-forex-border p-6">
          <h2 className="text-lg font-semibold mb-4">Risk Management</h2>
          <div className="grid grid-cols-2 gap-6">
            <RiskBar
              label="Daily P&L"
              current={risk.summary.daily_pnl}
              limit={risk.summary.daily_limit}
              percent={risk.summary.daily_percent}
            />
            <RiskBar
              label="Weekly P&L"
              current={risk.summary.weekly_pnl}
              limit={risk.summary.weekly_limit}
              percent={risk.summary.weekly_percent}
            />
          </div>
        </div>
      )}

      {/* Open Positions */}
      <div className="bg-forex-card rounded-xl border border-forex-border p-6">
        <h2 className="text-lg font-semibold mb-4">Open Positions</h2>
        {positions.length === 0 ? (
          <p className="text-gray-400 text-center py-8">No open positions</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-gray-400 text-sm border-b border-forex-border">
                  <th className="text-left py-2">Ticket</th>
                  <th className="text-left py-2">Type</th>
                  <th className="text-left py-2">Volume</th>
                  <th className="text-left py-2">Open Price</th>
                  <th className="text-left py-2">Current</th>
                  <th className="text-left py-2">P&L</th>
                  <th className="text-left py-2">SL</th>
                  <th className="text-left py-2">TP</th>
                </tr>
              </thead>
              <tbody>
                {positions.map(pos => (
                  <tr key={pos.ticket} className="border-b border-forex-border/50">
                    <td className="py-3">#{pos.ticket}</td>
                    <td>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        pos.type === 'BUY' ? 'bg-forex-green/20 text-forex-green' : 'bg-forex-red/20 text-forex-red'
                      }`}>
                        {pos.type}
                      </span>
                    </td>
                    <td>{pos.volume}</td>
                    <td>{pos.open_price.toFixed(5)}</td>
                    <td>{pos.current_price.toFixed(5)}</td>
                    <td className={pos.profit >= 0 ? 'text-forex-green' : 'text-forex-red'}>
                      ${pos.profit.toFixed(2)}
                    </td>
                    <td>{pos.sl.toFixed(5)}</td>
                    <td>{pos.tp.toFixed(5)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Upcoming News */}
      <div className="bg-forex-card rounded-xl border border-forex-border p-6">
        <h2 className="text-lg font-semibold mb-4">Upcoming News Events</h2>
        {news.events?.length === 0 ? (
          <p className="text-gray-400 text-center py-8">No upcoming events</p>
        ) : (
          <div className="space-y-3">
            {news.events?.slice(0, 10).map((event, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <ImpactBadge impact={event.impact} />
                  <div>
                    <p className="font-medium">{event.title}</p>
                    <p className="text-sm text-gray-400">{event.currency}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm">{new Date(event.time).toLocaleString()}</p>
                  <p className="text-xs text-gray-400">
                    {event.minutes_until > 0 ? `in ${Math.round(event.minutes_until)} min` : 'Past'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatusCard({ title, value, icon, color, subtitle }) {
  const colorClasses = {
    green: 'bg-forex-green/20 text-forex-green',
    red: 'bg-forex-red/20 text-forex-red',
    blue: 'bg-forex-blue/20 text-forex-blue',
    yellow: 'bg-forex-yellow/20 text-forex-yellow',
    purple: 'bg-forex-purple/20 text-forex-purple'
  }

  return (
    <div className="bg-forex-card rounded-xl border border-forex-border p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400">{title}</span>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  )
}

function RiskBar({ label, current, limit, percent }) {
  const isPositive = current >= 0
  const barWidth = Math.min(Math.abs(percent) / 10 * 100, 100)

  return (
    <div>
      <div className="flex justify-between mb-2">
        <span className="text-sm text-gray-400">{label}</span>
        <span className={`text-sm font-medium ${isPositive ? 'text-forex-green' : 'text-forex-red'}`}>
          ${current.toFixed(2)} / ${limit.toFixed(2)}
        </span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${isPositive ? 'bg-forex-green' : 'bg-forex-red'}`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 mt-1">{percent.toFixed(1)}% of limit</p>
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
