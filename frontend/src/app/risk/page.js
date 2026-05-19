'use client'

import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import appConfig from '../../config'

export default function RiskPage() {
  const [risk, setRisk] = useState(null)

  useEffect(() => {
    fetchRisk()
    const interval = setInterval(fetchRisk, 10000)
    return () => clearInterval(interval)
  }, [])

  const fetchRisk = async () => {
    const res = await fetch(`${appConfig.API_URL}/risk`)
    if (res.ok) setRisk(await res.json())
  }

  if (!risk) return <div className="p-6">Loading...</div>

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Risk Management</h1>

      {/* Risk Limits */}
      <div className="grid grid-cols-2 gap-6">
        <RiskCard
          title="Daily Risk"
          current={risk.summary?.daily_pnl || 0}
          limit={risk.summary?.daily_limit || 0}
          percent={risk.summary?.daily_percent || 0}
          remaining={risk.summary?.daily_remaining || 0}
        />
        <RiskCard
          title="Weekly Risk"
          current={risk.summary?.weekly_pnl || 0}
          limit={risk.summary?.weekly_limit || 0}
          percent={risk.summary?.weekly_percent || 0}
          remaining={risk.summary?.weekly_remaining || 0}
        />
      </div>

      {/* Trade Statistics */}
      <div className="bg-forex-card rounded-xl border border-forex-border p-6">
        <h2 className="text-lg font-semibold mb-4">Trade Statistics</h2>
        <div className="grid grid-cols-4 gap-4">
          <StatBox label="Total Trades" value={risk.stats?.total_trades || 0} />
          <StatBox label="Win Rate" value={`${risk.stats?.win_rate || 0}%`} color="green" />
          <StatBox label="Profit Factor" value={risk.stats?.profit_factor || 0} />
          <StatBox label="Net P&L" value={`$${risk.stats?.net_pnl || 0}`} color={risk.stats?.net_pnl >= 0 ? 'green' : 'red'} />
        </div>
      </div>

      {/* Win/Loss Chart */}
      <div className="bg-forex-card rounded-xl border border-forex-border p-6">
        <h2 className="text-lg font-semibold mb-4">Win/Loss Distribution</h2>
        <div className="grid grid-cols-4 gap-4">
          <StatBox label="Winning Trades" value={risk.stats?.winning_trades || 0} color="green" />
          <StatBox label="Losing Trades" value={risk.stats?.losing_trades || 0} color="red" />
          <StatBox label="Avg Win" value={`$${risk.stats?.avg_win || 0}`} color="green" />
          <StatBox label="Avg Loss" value={`$${risk.stats?.avg_loss || 0}`} color="red" />
        </div>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <StatBox label="Best Trade" value={`$${risk.stats?.best_trade || 0}`} color="green" />
          <StatBox label="Worst Trade" value={`$${risk.stats?.worst_trade || 0}`} color="red" />
        </div>
      </div>

      {/* News Blackout Status */}
      <div className={`rounded-xl border p-6 ${
        risk.summary?.news_blackout
          ? 'bg-yellow-500/10 border-yellow-500/50'
          : 'bg-forex-card border-forex-border'
      }`}>
        <h2 className="text-lg font-semibold mb-2">News Filter Status</h2>
        <p className={risk.summary?.news_blackout ? 'text-yellow-400' : 'text-forex-green'}>
          {risk.summary?.news_blackout ? 'BLACKOUT ACTIVE' : 'Trading Allowed'}
        </p>
        {risk.summary?.blackout_reason && (
          <p className="text-sm text-gray-400 mt-1">{risk.summary.blackout_reason}</p>
        )}
      </div>
    </div>
  )
}

function RiskCard({ title, current, limit, percent, remaining }) {
  const isPositive = current >= 0
  const barWidth = Math.min(Math.abs(percent) / 10 * 100, 100)

  return (
    <div className="bg-forex-card rounded-xl border border-forex-border p-6">
      <h3 className="text-gray-400 mb-4">{title}</h3>
      <div className="flex justify-between mb-2">
        <span className={`text-2xl font-bold ${isPositive ? 'text-forex-green' : 'text-forex-red'}`}>
          ${current.toFixed(2)}
        </span>
        <span className="text-gray-400">/ ${limit.toFixed(2)}</span>
      </div>
      <div className="h-3 bg-gray-800 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full rounded-full ${isPositive ? 'bg-forex-green' : 'bg-forex-red'}`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">{percent.toFixed(1)}% used</span>
        <span className={remaining >= 0 ? 'text-forex-green' : 'text-forex-red'}>
          ${remaining.toFixed(2)} remaining
        </span>
      </div>
    </div>
  )
}

function StatBox({ label, value, color }) {
  const colorClasses = {
    green: 'text-forex-green',
    red: 'text-forex-red',
    blue: 'text-forex-blue'
  }

  return (
    <div className="bg-gray-800/50 rounded-lg p-4">
      <p className="text-sm text-gray-400">{label}</p>
      <p className={`text-xl font-bold mt-1 ${colorClasses[color] || 'text-white'}`}>
        {value}
      </p>
    </div>
  )
}
