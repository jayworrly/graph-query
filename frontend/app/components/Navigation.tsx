'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart3, Search, RefreshCw } from 'lucide-react'

export default function Navigation() {
  const pathname = usePathname()

  return (
    <nav className="border-b border-slate-700/50 bg-slate-900/30 backdrop-blur-sm">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-2">
            <BarChart3 className="h-8 w-8 text-purple-400" />
            <span className="text-xl font-bold text-white">Ballistic</span>
          </div>

          {/* Navigation Links */}
          <div className="flex items-center space-x-1">
            <Link
              href="/"
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-colors ${
                pathname === '/'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-300 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              <div className="flex items-center space-x-2">
                <BarChart3 className="h-4 w-4" />
                <span>Dashboard</span>
              </div>
            </Link>
            <Link
              href="/explore"
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-colors ${
                pathname === '/explore'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-300 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Search className="h-4 w-4" />
                <span>Explore</span>
              </div>
            </Link>
          </div>

          {/* Right side controls */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-slate-800/50 rounded-lg px-3 py-2">
              <Search className="h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search tokens..."
                className="bg-transparent text-sm text-white placeholder-gray-400 border-none outline-none w-40"
              />
            </div>
            <select className="bg-slate-800/50 text-white text-sm rounded-lg px-3 py-2 border border-slate-600/50">
              <option>24H</option>
              <option>7D</option>
              <option>30D</option>
            </select>
            <button className="p-2 text-gray-400 hover:text-white transition-colors">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
} 