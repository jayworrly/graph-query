'use client'

import { useState, useEffect } from 'react'
import { Search, Brain, TrendingUp, Activity, DollarSign, Users, ArrowRight, Trophy, Medal, Award } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface TopPerformer {
  address: string
  label?: string
  totalPnl: number
  totalTrades: number
  winRate: number
  totalVolume: number
}

export default function IntelPage() {
  const [searchValue, setSearchValue] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [topPerformers, setTopPerformers] = useState<TopPerformer[]>([])
  const [searchSuggestions, setSearchSuggestions] = useState<any[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const router = useRouter()

  // Fetch top performers on page load
  useEffect(() => {
    fetchTopPerformers()
  }, [])

  // Fetch search suggestions as user types
  useEffect(() => {
    if (searchValue.length >= 3) {
      const timeoutId = setTimeout(() => {
        fetchSearchSuggestions(searchValue)
      }, 300)
      return () => clearTimeout(timeoutId)
    } else {
      setSearchSuggestions([])
      setShowSuggestions(false)
    }
  }, [searchValue])

  const fetchTopPerformers = async () => {
    try {
      const response = await fetch('/api/wallet/top-performers?limit=10&metric=pnl')
      const result = await response.json()
      if (result.success) {
        setTopPerformers(result.data.performers)
      }
    } catch (error) {
      console.error('Failed to fetch top performers:', error)
    }
  }

  const fetchSearchSuggestions = async (query: string) => {
    try {
      const response = await fetch(`/api/wallet/search?q=${encodeURIComponent(query)}&limit=5`)
      const result = await response.json()
      if (result.success) {
        setSearchSuggestions(result.data.wallets)
        setShowSuggestions(true)
      }
    } catch (error) {
      console.error('Failed to fetch search suggestions:', error)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchValue.trim()) return

    // Basic validation for wallet address format
    const isValidAddress = /^0x[a-fA-F0-9]{40}$/.test(searchValue.trim())
    if (!isValidAddress) {
      alert('Please enter a valid wallet address (0x...)')
      return
    }

    setIsSearching(true)
    setShowSuggestions(false)
    // Navigate to wallet detail page
    router.push(`/intel/wallet/${searchValue.trim()}`)
  }

  const handleSuggestionClick = (address: string) => {
    setSearchValue(address)
    setShowSuggestions(false)
    router.push(`/intel/wallet/${address}`)
  }

  const handleTopPerformerClick = (address: string) => {
    router.push(`/intel/wallet/${address}`)
  }

  const recentSearches = [
    '0xf820Fe335130468169dF696Fe30D1D3e740A7D0a',
    '0x742d35cc1558db2c6b0d7c2dbf0f6e6d9a8b4c3f',
    '0x1234567890123456789012345678901234567890'
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f0f23] via-[#1a1a2e] to-[#16213e] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12 pt-8">
          <div className="flex items-center justify-center mb-6">
            <div className="w-16 h-16 bg-gradient-to-br from-primaryBlue to-primaryPurple rounded-2xl flex items-center justify-center shadow-2xl">
              <Brain className="h-8 w-8 text-white" />
            </div>
          </div>
          <h1 className="text-5xl font-bold bg-gradient-to-r from-primaryBlue to-primaryPurple bg-clip-text text-transparent mb-4">
            Arena Intel
          </h1>
          <p className="text-xl text-textSecondary max-w-2xl mx-auto">
            Deep wallet analysis and intelligence for the Arena ecosystem. 
            Discover trading patterns, profitability, and behavioral insights.
          </p>
        </div>

        {/* Search Section */}
        <div className="max-w-4xl mx-auto mb-16 relative">
          <form onSubmit={handleSearch} className="relative">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-6 flex items-center pointer-events-none">
                <Search className="h-6 w-6 text-textSecondary" />
              </div>
              <input
                type="text"
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                onFocus={() => searchSuggestions.length > 0 && setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                placeholder="Enter wallet address (0x...) or search by label"
                className="w-full pl-16 pr-32 py-6 text-lg bg-backgroundSecondary/50 border border-primaryStroke/30 rounded-2xl text-textPrimary placeholder-textSecondary focus:outline-none focus:ring-2 focus:ring-primaryBlue/50 focus:border-primaryBlue/50 backdrop-blur-sm transition-all"
              />
              <button
                type="submit"
                disabled={isSearching || !searchValue.trim()}
                className="absolute inset-y-0 right-0 mr-3 px-8 bg-gradient-to-r from-primaryBlue to-primaryPurple text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-primaryBlue/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {isSearching ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          </form>

          {/* Search Suggestions */}
          {showSuggestions && searchSuggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-backgroundSecondary/90 border border-primaryStroke/30 rounded-xl shadow-xl backdrop-blur-xl z-50">
              {searchSuggestions.map((wallet, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(wallet.address)}
                  className="w-full px-6 py-3 text-left hover:bg-primaryStroke/20 transition-colors border-b border-primaryStroke/10 last:border-b-0"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-textPrimary">
                        {wallet.label || 'Unknown Wallet'}
                      </div>
                      <div className="text-xs text-textSecondary font-mono">
                        {wallet.address.substring(0, 6)}...{wallet.address.substring(wallet.address.length - 4)}
                      </div>
                    </div>
                    <div className="text-xs text-textSecondary">
                      {wallet.tradeCount} trades
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Recent Searches */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-textSecondary mb-3">Recent Searches</h3>
            <div className="flex flex-wrap gap-2">
              {recentSearches.map((address, index) => (
                <button
                  key={index}
                  onClick={() => setSearchValue(address)}
                  className="px-4 py-2 bg-backgroundTertiary/30 border border-primaryStroke/20 rounded-xl text-sm text-textSecondary hover:text-textPrimary hover:border-primaryBlue/30 transition-all"
                >
                  {address.substring(0, 6)}...{address.substring(address.length - 4)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Top Performers */}
        <div className="mb-16">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-3xl font-bold text-textPrimary flex items-center space-x-3">
              <Trophy className="h-8 w-8 text-primaryGold" />
              <span>Top Performers</span>
            </h2>
            <button className="text-primaryBlue hover:text-primaryPurple transition-colors font-medium">
              View All
            </button>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {topPerformers.slice(0, 6).map((performer, index) => (
              <button
                key={performer.address}
                onClick={() => handleTopPerformerClick(performer.address)}
                className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm hover:border-primaryBlue/40 transition-all text-left group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    {index === 0 && <Trophy className="h-5 w-5 text-primaryGold" />}
                    {index === 1 && <Medal className="h-5 w-5 text-gray-400" />}
                    {index === 2 && <Award className="h-5 w-5 text-amber-600" />}
                    {index >= 3 && <span className="text-textSecondary font-bold">#{index + 1}</span>}
                  </div>
                  <ArrowRight className="h-4 w-4 text-textSecondary group-hover:text-primaryBlue transition-colors" />
                </div>
                
                <div className="mb-3">
                  <h3 className="font-semibold text-textPrimary mb-1">
                    {performer.label || 'Unknown Wallet'}
                  </h3>
                  <p className="text-xs text-textSecondary font-mono">
                    {performer.address.substring(0, 6)}...{performer.address.substring(performer.address.length - 4)}
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-textSecondary">P&L</span>
                    <span className={`text-sm font-medium ${performer.totalPnl >= 0 ? 'text-primaryGreen' : 'text-red-500'}`}>
                      {performer.totalPnl >= 0 ? '+' : ''}${performer.totalPnl.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-textSecondary">Win Rate</span>
                    <span className="text-sm font-medium text-textPrimary">{performer.winRate.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-textSecondary">Trades</span>
                    <span className="text-sm font-medium text-textPrimary">{performer.totalTrades}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <div className="w-12 h-12 bg-primaryGreen/20 rounded-xl flex items-center justify-center mb-4">
              <TrendingUp className="h-6 w-6 text-primaryGreen" />
            </div>
            <h3 className="text-lg font-semibold text-textPrimary mb-2">P&L Analysis</h3>
            <p className="text-sm text-textSecondary">
              Track wallet profitability across all Arena token trades with detailed profit and loss metrics.
            </p>
          </div>

          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <div className="w-12 h-12 bg-primaryBlue/20 rounded-xl flex items-center justify-center mb-4">
              <Activity className="h-6 w-6 text-primaryBlue" />
            </div>
            <h3 className="text-lg font-semibold text-textPrimary mb-2">Trading Activity</h3>
            <p className="text-sm text-textSecondary">
              Analyze trading patterns, frequency, and timing across the Arena ecosystem.
            </p>
          </div>

          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <div className="w-12 h-12 bg-primaryPurple/20 rounded-xl flex items-center justify-center mb-4">
              <DollarSign className="h-6 w-6 text-primaryPurple" />
            </div>
            <h3 className="text-lg font-semibold text-textPrimary mb-2">Token Holdings</h3>
            <p className="text-sm text-textSecondary">
              View current and historical token positions with valuation insights.
            </p>
          </div>

          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <div className="w-12 h-12 bg-primaryOrange/20 rounded-xl flex items-center justify-center mb-4">
              <Users className="h-6 w-6 text-primaryOrange" />
            </div>
            <h3 className="text-lg font-semibold text-textPrimary mb-2">Wallet Labels</h3>
            <p className="text-sm text-textSecondary">
              Identify known wallets with meaningful labels and user associations.
            </p>
          </div>
        </div>

        {/* Sample Analysis Teaser */}
        <div className="bg-backgroundSecondary/20 border border-primaryStroke/20 rounded-2xl p-8 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-textPrimary">Sample Wallet Analysis</h2>
            <ArrowRight className="h-5 w-5 text-primaryBlue" />
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-primaryGreen mb-2">+$42,350</div>
              <div className="text-sm text-textSecondary">Total P&L</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primaryBlue mb-2">127</div>
              <div className="text-sm text-textSecondary">Total Trades</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primaryPurple mb-2">89%</div>
              <div className="text-sm text-textSecondary">Win Rate</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 