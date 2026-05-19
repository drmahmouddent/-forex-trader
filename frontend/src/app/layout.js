import './globals.css'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Forex Trader - EUR/USD Automated Trading',
  description: 'Automated forex trading system with news filter',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="flex h-screen">
          {/* Sidebar */}
          <aside className="w-64 bg-forex-card border-r border-forex-border">
            <div className="p-4 border-b border-forex-border">
              <h1 className="text-xl font-bold text-forex-blue">Forex Trader</h1>
              <p className="text-sm text-gray-400">EUR/USD Bot</p>
            </div>
            <nav className="p-4 space-y-2">
              <a href="/" className="block px-4 py-2 rounded-lg bg-forex-blue/20 text-forex-blue">
                Dashboard
              </a>
              <a href="/positions" className="block px-4 py-2 rounded-lg hover:bg-gray-800 text-gray-300">
                Positions
              </a>
              <a href="/news" className="block px-4 py-2 rounded-lg hover:bg-gray-800 text-gray-300">
                News Calendar
              </a>
              <a href="/strategies" className="block px-4 py-2 rounded-lg hover:bg-gray-800 text-gray-300">
                Strategies
              </a>
              <a href="/risk" className="block px-4 py-2 rounded-lg hover:bg-gray-800 text-gray-300">
                Risk Manager
              </a>
              <a href="/settings" className="block px-4 py-2 rounded-lg hover:bg-gray-800 text-gray-300">
                Settings
              </a>
            </nav>
          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
