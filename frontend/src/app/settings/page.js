'use client'

import { useState, useEffect } from 'react'
import appConfig from '../../config'

export default function SettingsPage() {
  const [config, setConfig] = useState(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    const res = await fetch(`${appConfig.API_URL}/config`)
    if (res.ok) setConfig(await res.json())
  }

  const saveConfig = async () => {
    const res = await fetch(`${appConfig.API_URL}/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    })
    if (res.ok) {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    }
  }

  if (!config) return <div className="p-6">Loading...</div>

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <button onClick={saveConfig} className="px-4 py-2 bg-forex-blue rounded-lg hover:bg-blue-600">
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>

      <div className="grid gap-6">
        {/* Trading Pair */}
        <SettingsSection title="Trading Pair">
          <SettingField label="Symbol" value={config.pair} disabled />
          <SettingField label="Timeframe" value={config.timeframe} disabled />
        </SettingsSection>

        {/* Risk Settings */}
        <SettingsSection title="Risk Management">
          <SettingField
            label="Risk Per Trade (%)"
            value={(config.risk_per_trade * 100).toFixed(1)}
            onChange={v => setConfig({...config, risk_per_trade: parseFloat(v) / 100})}
          />
          <SettingField
            label="Max Daily Loss (%)"
            value={(config.max_daily_loss * 100).toFixed(1)}
            onChange={v => setConfig({...config, max_daily_loss: parseFloat(v) / 100})}
          />
          <SettingField
            label="Max Weekly Loss (%)"
            value={(config.max_weekly_loss * 100).toFixed(1)}
            onChange={v => setConfig({...config, max_weekly_loss: parseFloat(v) / 100})}
          />
          <SettingField
            label="Max Open Trades"
            value={config.max_open_trades}
            onChange={v => setConfig({...config, max_open_trades: parseInt(v)})}
          />
        </SettingsSection>

        {/* News Settings */}
        <SettingsSection title="News Filter">
          <SettingToggle
            label="Enable News Filter"
            value={config.news_filter_enabled}
            onChange={v => setConfig({...config, news_filter_enabled: v})}
          />
          <SettingField
            label="Blackout Window (minutes)"
            value={config.news_buffer_minutes}
            onChange={v => setConfig({...config, news_buffer_minutes: parseInt(v)})}
          />
        </SettingsSection>
      </div>
    </div>
  )
}

function SettingsSection({ title, children }) {
  return (
    <div className="bg-forex-card rounded-xl border border-forex-border p-6">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>
      <div className="space-y-4">
        {children}
      </div>
    </div>
  )
}

function SettingField({ label, value, onChange, disabled }) {
  return (
    <div className="flex items-center justify-between">
      <label className="text-gray-400">{label}</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange?.(e.target.value)}
        disabled={disabled}
        className="w-32 px-3 py-2 bg-gray-800 border border-forex-border rounded-lg text-right disabled:opacity-50"
      />
    </div>
  )
}

function SettingToggle({ label, value, onChange }) {
  return (
    <div className="flex items-center justify-between">
      <label className="text-gray-400">{label}</label>
      <button
        onClick={() => onChange(!value)}
        className={`w-12 h-6 rounded-full transition-colors ${
          value ? 'bg-forex-green' : 'bg-gray-600'
        }`}
      >
        <div className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${
          value ? 'translate-x-6' : 'translate-x-0.5'
        }`} />
      </button>
    </div>
  )
}
