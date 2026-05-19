'use client'

import { useState, useEffect } from 'react'
import config from '../../config'

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState([])

  useEffect(() => {
    fetchStrategies()
  }, [])

  const fetchStrategies = async () => {
    const res = await fetch(`${config.API_URL}/strategies`)
    if (res.ok) setStrategies(await res.json())
  }

  const toggleStrategy = async (name, enabled) => {
    const endpoint = enabled ? 'disable' : 'enable'
    await fetch(`${config.API_URL}/strategies/${name}/${endpoint}`, { method: 'POST' })
    fetchStrategies()
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Trading Strategies</h1>

      <div className="grid gap-4">
        {strategies.map(strategy => (
          <div key={strategy.name} className="bg-forex-card rounded-xl border border-forex-border p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">{strategy.name}</h2>
                <p className="text-sm text-gray-400 mt-1">
                  {getStrategyDescription(strategy.name)}
                </p>
              </div>
              <button
                onClick={() => toggleStrategy(strategy.name, strategy.enabled)}
                className={`px-4 py-2 rounded-lg font-medium ${
                  strategy.enabled
                    ? 'bg-forex-green/20 text-forex-green hover:bg-forex-green/30'
                    : 'bg-gray-600/20 text-gray-400 hover:bg-gray-600/30'
                }`}
              >
                {strategy.enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-4">
              <StrategyStat label="Win Rate" value={getStrategyWinRate(strategy.name)} />
              <StrategyStat label="R:R Ratio" value={getStrategyRR(strategy.name)} />
              <StrategyStat label="Best Session" value={getStrategySession(strategy.name)} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function StrategyStat({ label, value }) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-lg font-medium mt-1">{value}</p>
    </div>
  )
}

function getStrategyDescription(name) {
  const descriptions = {
    'London Breakout': 'Trades the breakout of Asian session range during London open. Best for volatile sessions.',
    'Trend Following': 'Uses EMA 9/21 crossover with RSI and MACD confirmation. Works best in trending markets.',
    'Support/Resistance': 'Trades bounces off key S/R levels with candlestick patterns. Best for ranging markets.'
  }
  return descriptions[name] || ''
}

function getStrategyWinRate(name) {
  const rates = {
    'London Breakout': '~60%',
    'Trend Following': '~55%',
    'Support/Resistance': '~65%'
  }
  return rates[name] || '-'
}

function getStrategyRR(name) {
  const rrs = {
    'London Breakout': '1:2',
    'Trend Following': '1:2',
    'Support/Resistance': '1:1.5'
  }
  return rrs[name] || '-'
}

function getStrategySession(name) {
  const sessions = {
    'London Breakout': 'London (7-10 UTC)',
    'Trend Following': 'All sessions',
    'Support/Resistance': 'Ranging markets'
  }
  return sessions[name] || '-'
}
