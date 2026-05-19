'use client'

import { useState, useEffect } from 'react'
import config from '../../config'

export default function PositionsPage() {
  const [positions, setPositions] = useState([])

  useEffect(() => {
    fetchPositions()
    const interval = setInterval(fetchPositions, 3000)
    return () => clearInterval(interval)
  }, [])

  const fetchPositions = async () => {
    const res = await fetch(`${config.API_URL}/positions`)
    if (res.ok) setPositions(await res.json())
  }

  const closePosition = async (ticket) => {
    if (confirm(`Close position #${ticket}?`)) {
      await fetch(`${config.API_URL}/positions/${ticket}/close`, { method: 'POST' })
      fetchPositions()
    }
  }

  const closeAll = async () => {
    if (confirm('Close ALL positions?')) {
      await fetch(`${config.API_URL}/positions/close-all`, { method: 'POST' })
      fetchPositions()
    }
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Open Positions</h1>
        {positions.length > 0 && (
          <button onClick={closeAll} className="px-4 py-2 bg-forex-red rounded-lg hover:bg-red-600">
            Close All
          </button>
        )}
      </div>

      <div className="bg-forex-card rounded-xl border border-forex-border overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="text-gray-400 text-sm bg-gray-800/50">
              <th className="text-left py-3 px-4">Ticket</th>
              <th className="text-left py-3 px-4">Type</th>
              <th className="text-left py-3 px-4">Volume</th>
              <th className="text-left py-3 px-4">Open Price</th>
              <th className="text-left py-3 px-4">Current</th>
              <th className="text-left py-3 px-4">P&L</th>
              <th className="text-left py-3 px-4">SL</th>
              <th className="text-left py-3 px-4">TP</th>
              <th className="text-left py-3 px-4">Open Time</th>
              <th className="text-left py-3 px-4">Action</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-12 text-center text-gray-400">
                  No open positions
                </td>
              </tr>
            ) : (
              positions.map(pos => (
                <tr key={pos.ticket} className="border-t border-forex-border/50 hover:bg-gray-800/30">
                  <td className="py-3 px-4">#{pos.ticket}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      pos.type === 'BUY' ? 'bg-forex-green/20 text-forex-green' : 'bg-forex-red/20 text-forex-red'
                    }`}>
                      {pos.type}
                    </span>
                  </td>
                  <td className="py-3 px-4">{pos.volume}</td>
                  <td className="py-3 px-4">{pos.open_price.toFixed(5)}</td>
                  <td className="py-3 px-4">{pos.current_price.toFixed(5)}</td>
                  <td className={`py-3 px-4 font-medium ${pos.profit >= 0 ? 'text-forex-green' : 'text-forex-red'}`}>
                    ${pos.profit.toFixed(2)}
                  </td>
                  <td className="py-3 px-4">{pos.sl.toFixed(5)}</td>
                  <td className="py-3 px-4">{pos.tp.toFixed(5)}</td>
                  <td className="py-3 px-4 text-sm text-gray-400">
                    {new Date(pos.open_time).toLocaleString()}
                  </td>
                  <td className="py-3 px-4">
                    <button onClick={() => closePosition(pos.ticket)} className="px-3 py-1 text-sm bg-forex-red/20 text-forex-red rounded hover:bg-forex-red/30">
                      Close
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
