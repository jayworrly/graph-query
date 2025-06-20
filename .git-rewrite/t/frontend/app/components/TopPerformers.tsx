'use client'

import { Trophy, TrendingUp, TrendingDown, ExternalLink, Loader2, Copy, RotateCcw } from 'lucide-react'
import { useState, useEffect } from 'react'
import { dexScreenerService, TopPerformerToken } from '../../lib/dexscreener.service'

export default function TopPerformers() {
  const [activeTab, setActiveTab] = useState<'performers' | 'graduated'>('performers')
  const [topPerformers, setTopPerformers] = useState<TopPerformerToken[]>([])
  const [graduatedTokens, setGraduatedTokens] = useState<TopPerformerToken[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Clear cache to force fresh data
      dexScreenerService.clearCache()
      
      const [performers, graduated] = await Promise.all([
        dexScreenerService.getTopPerformers(5),
        dexScreenerService.getGraduatedTokens(5)
      ])
      
      console.log('Fetched performers:', performers)
      console.log('Fetched graduated:', graduated)
      
      setTopPerformers(performers)
      setGraduatedTokens(graduated)
      setLastUpdated(new Date())
    } catch (err) {
      setError('Failed to fetch token data')
      console.error('Error fetching top performers:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    
    // Refresh data every 10 seconds for testing
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const formatAddress = (address: string) => {
    return `${address.slice(0, 6)}...${address.slice(-4)}`
  }

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    return `${Math.floor(diffHours / 24)}d ago`
  }

  const renderTokenList = (tokens: TopPerformerToken[]) => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Loader2 className="h-8 w-8 text-purple-400 animate-spin mb-4" />
          <p className="text-sm text-gray-400">Loading top performers...</p>
        </div>
      )
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Trophy className="h-12 w-12 text-gray-500 mb-4" />
          <h4 className="text-lg font-medium text-gray-300 mb-2">Failed to load data</h4>
          <p className="text-sm text-gray-500 mb-4">{error}</p>
          <button
            onClick={fetchData}
            className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            <RotateCcw className="h-4 w-4" />
            <span>Retry</span>
          </button>
        </div>
      )
    }

    if (tokens.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Trophy className="h-12 w-12 text-gray-500 mb-4" />
          <h4 className="text-lg font-medium text-gray-300 mb-2">No tokens found</h4>
          <p className="text-sm text-gray-500">Check back later for updated data.</p>
        </div>
      )
    }

    return tokens.map((token) => (
      <div
        key={`${token.address}-${token.rank}`}
        className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors group"
      >
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-8 h-8 bg-yellow-500/20 rounded-full text-yellow-400 font-bold text-sm">
            {token.rank}
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-lg">{token.icon}</span>
            <div>
              <div className="font-medium text-white">{token.name}</div>
              <div className={`text-sm flex items-center space-x-2 ${
                token.dex ? 'text-blue-400' : 'text-gray-400'
              }`}>
                <span>{token.symbol}{token.dex ? ' DEX' : ''}</span>
                <button
                  onClick={() => copyToClipboard(token.address)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Copy address"
                >
                  <Copy className="h-3 w-3 hover:text-white" />
                </button>
              </div>
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="font-medium text-white">{token.price}</div>
          <div className={`text-sm flex items-center space-x-1 ${
            token.positive ? 'text-green-400' : 'text-red-400'
          }`}>
            {token.positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            <span>{token.change}</span>
          </div>
          {token.volume24h && (
            <div className="text-xs text-gray-500">
              Vol: ${(token.volume24h / 1000).toFixed(1)}K
            </div>
          )}
        </div>
      </div>
    ))
  }

  return (
    <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Trophy className="h-5 w-5 text-yellow-400" />
          <h3 className="text-xl font-semibold text-white">Top Performers</h3>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setActiveTab('performers')}
            className={`px-3 py-1 text-xs rounded ${
              activeTab === 'performers'
                ? 'bg-purple-600 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Gainers
          </button>
          <button
            onClick={() => setActiveTab('graduated')}
            className={`px-3 py-1 text-xs rounded ${
              activeTab === 'graduated'
                ? 'bg-green-600/20 text-green-400 border border-green-600/30'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            DEX Tokens
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center space-x-1 px-2 py-1 text-xs text-gray-400 hover:text-white disabled:opacity-50"
            title="Refresh data"
          >
            <RotateCcw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Last updated info */}
      <div className="flex items-center justify-between mb-4 text-xs text-gray-500">
        <span>Last updated: {formatTimeAgo(lastUpdated)}</span>
        <span>Data from DexScreener</span>
      </div>

      <div className="space-y-4">
        {activeTab === 'performers' && renderTokenList(topPerformers)}
        {activeTab === 'graduated' && renderTokenList(graduatedTokens)}
      </div>
    </div>
  )
} 