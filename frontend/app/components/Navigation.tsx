'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart3, Search, RefreshCw, Zap, TrendingUp, Settings, Bell, User, ExternalLink } from 'lucide-react'
import { useState } from 'react'

export default function Navigation() {
  const pathname = usePathname()
  const [searchValue, setSearchValue] = useState('')

  const handleRefresh = () => {
    window.location.reload()
  }

  const openArenaApp = () => {
    window.open('https://arena.avax.network', '_blank')
  }

  return (
    <nav className="border-b border-primaryStroke/30 bg-gradient-to-r from-backgroundSecondary/80 via-backgroundSecondary/60 to-backgroundSecondary/80 backdrop-blur-xl shadow-lg w-full">
      <div className="w-full px-6">
        <div className="flex items-center justify-between h-18">
          {/* Left side - Logo & Navigation Links */}
          <div className="flex items-center space-x-8">
            {/* Logo & Brand */}
            <div className="flex items-center space-x-3">
              <div className="relative">
                <div className="w-10 h-10 bg-gradient-to-br from-primaryBlue to-primaryPurple rounded-lg flex items-center justify-center shadow-lg">
                  <Zap className="h-6 w-6 text-white" />
                </div>
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-primaryGreen rounded-full border-2 border-background animate-pulse"></div>
              </div>
              <div className="flex flex-col">
                <span className="text-2xl font-bold bg-gradient-to-r from-primaryBlue to-primaryPurple bg-clip-text text-transparent">
                  Arena
                </span>
                <span className="text-xs text-textSecondary font-medium">
                  Terminal
                </span>
              </div>
            </div>

            {/* Navigation Links */}
            <div className="flex items-center space-x-2">
              <Link
                href="/"
                className={`px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200 ${
                  pathname === '/'
                    ? 'bg-gradient-to-r from-primaryBlue to-primaryPurple text-white shadow-lg shadow-primaryBlue/25'
                    : 'text-textSecondary hover:text-textPrimary hover:bg-primaryStroke/30'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <BarChart3 className="h-4 w-4" />
                  <span>Dashboard</span>
                </div>
              </Link>
              <Link
                href="/explore"
                className={`px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200 ${
                  pathname === '/explore'
                    ? 'bg-gradient-to-r from-primaryBlue to-primaryPurple text-white shadow-lg shadow-primaryBlue/25'
                    : 'text-textSecondary hover:text-textPrimary hover:bg-primaryStroke/30'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Search className="h-4 w-4" />
                  <span>Explore</span>
                </div>
              </Link>
              <button
                onClick={openArenaApp}
                className="px-6 py-3 rounded-xl text-sm font-semibold text-textSecondary hover:text-textPrimary hover:bg-primaryStroke/30 transition-all duration-200"
              >
                <div className="flex items-center space-x-2">
                  <ExternalLink className="h-4 w-4" />
                  <span>Launch App</span>
                </div>
              </button>
            </div>
          </div>

          {/* Right side controls */}
          <div className="flex items-center space-x-4">
            {/* Search Bar */}
            <div className="relative">
              <div className="flex items-center space-x-2 bg-backgroundTertiary/50 border border-primaryStroke/30 rounded-xl px-4 py-2.5 backdrop-blur-sm">
                <Search className="h-4 w-4 text-textSecondary" />
                <input
                  type="text"
                  placeholder="Search tokens..."
                  value={searchValue}
                  onChange={(e) => setSearchValue(e.target.value)}
                  className="bg-transparent text-sm text-textPrimary placeholder-textSecondary border-none outline-none w-48 font-medium"
                />
              </div>
              {searchValue && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-backgroundSecondary border border-primaryStroke/30 rounded-xl shadow-xl backdrop-blur-xl z-50">
                  <div className="p-3 text-sm text-textSecondary">
                    Search functionality coming soon...
                  </div>
                </div>
              )}
            </div>

            {/* Time Range Selector */}
            <select className="bg-backgroundTertiary/50 border border-primaryStroke/30 text-textPrimary text-sm font-medium rounded-xl px-4 py-2.5 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-primaryBlue/50 focus:border-primaryBlue/50 transition-all">
              <option value="24h">24H</option>
              <option value="7d">7D</option>
              <option value="30d">30D</option>
              <option value="90d">90D</option>
            </select>

            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              <button 
                onClick={handleRefresh}
                className="p-2.5 text-textSecondary hover:text-textPrimary hover:bg-primaryStroke/30 rounded-xl transition-all duration-200 group"
                title="Refresh Data"
              >
                <RefreshCw className="h-4 w-4 group-hover:rotate-180 transition-transform duration-500" />
              </button>
              
              <button className="p-2.5 text-textSecondary hover:text-textPrimary hover:bg-primaryStroke/30 rounded-xl transition-all duration-200 relative">
                <Bell className="h-4 w-4" />
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-primaryGreen rounded-full"></div>
              </button>
              
              <button className="p-2.5 text-textSecondary hover:text-textPrimary hover:bg-primaryStroke/30 rounded-xl transition-all duration-200">
                <Settings className="h-4 w-4" />
              </button>
            </div>

            {/* User Profile */}
            <div className="flex items-center space-x-3 bg-backgroundTertiary/30 border border-primaryStroke/20 rounded-xl px-4 py-2">
              <div className="w-8 h-8 bg-gradient-to-br from-primaryGreen to-primaryBlue rounded-lg flex items-center justify-center">
                <User className="h-4 w-4 text-white" />
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-semibold text-textPrimary">Trader</span>
                <span className="text-xs text-textSecondary">Connected</span>
              </div>
            </div>

            {/* Network Status */}
            <div className="flex items-center space-x-2 bg-primaryGreen/10 border border-primaryGreen/20 rounded-xl px-3 py-2">
              <div className="w-2 h-2 bg-primaryGreen rounded-full animate-pulse"></div>
              <span className="text-xs font-semibold text-primaryGreen">AVAX</span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
} 