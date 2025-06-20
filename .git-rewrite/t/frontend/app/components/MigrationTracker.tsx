'use client'

import { ArrowUpRight, Clock, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react'
import { useState, useEffect } from 'react'

interface MigrationToken {
  name: string
  symbol: string
  address: string
  progress: number
  timeLeft: string
  currentPrice: number
  volume24h: number
  status: 'bonding' | 'ready' | 'migrated'
  change24h: number
}

export default function MigrationTracker() {
  const [tokens, setTokens] = useState<MigrationToken[]>([])
  const [activeFilter, setActiveFilter] = useState<'all' | 'bonding' | 'ready' | 'migrated'>('all')

  useEffect(() => {
    const fetchMigrationData = async () => {
      try {
        const response = await fetch(`/api/tokens/migration-tracker?filter=${activeFilter}`)
        const data = await response.json()
        
        if (data.success && data.data.tokens) {
          setTokens(data.data.tokens)
        }
      } catch (error) {
        console.error('Error fetching migration data:', error)
        setTokens([])
      }
    }

    fetchMigrationData()
    const interval = setInterval(fetchMigrationData, 30000) // Update every 30 seconds
    
    return () => clearInterval(interval)
  }, [activeFilter])

  const filteredTokens = tokens.filter(token => 
    activeFilter === 'all' || token.status === activeFilter
  )

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'bonding':
        return <Clock className="h-4 w-4 text-yellow-400" />
      case 'ready':
        return <AlertCircle className="h-4 w-4 text-orange-400" />
      case 'migrated':
        return <CheckCircle className="h-4 w-4 text-green-400" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'bonding':
        return 'border-yellow-500/30 bg-yellow-500/10'
      case 'ready':
        return 'border-orange-500/30 bg-orange-500/10'
      case 'migrated':
        return 'border-green-500/30 bg-green-500/10'
      default:
        return 'border-gray-500/30 bg-gray-500/10'
    }
  }

  const formatCurrency = (value: number | undefined) => {
    const numValue = Number(value) || 0
    return `$${numValue.toFixed(5)}`
  }

  const formatVolume = (value: number | undefined) => {
    const numValue = Number(value) || 0
    return `$${(numValue / 1000).toFixed(0)}K`
  }

  const filters = [
    { key: 'all' as const, label: 'All Tokens', count: tokens.length },
    { key: 'bonding' as const, label: 'Bonding', count: tokens.filter(t => t.status === 'bonding').length },
    { key: 'ready' as const, label: 'Ready to Migrate', count: tokens.filter(t => t.status === 'ready').length },
    { key: 'migrated' as const, label: 'Migrated', count: tokens.filter(t => t.status === 'migrated').length }
  ]

  return (
    <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-slate-700/50">
        <div className="flex items-center space-x-2">
          <ArrowUpRight className="h-5 w-5 text-purple-400" />
          <h3 className="text-xl font-semibold text-white">Migration Tracker</h3>
        </div>
        
        <div className="text-sm text-gray-400">
          {filteredTokens.length} tokens
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex space-x-2 px-6 py-4 border-b border-slate-700/50 overflow-x-auto">
        {filters.map((filter) => (
          <button
            key={filter.key}
            onClick={() => setActiveFilter(filter.key)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg whitespace-nowrap transition-colors ${
              activeFilter === filter.key
                ? 'bg-purple-600/20 text-purple-400 border border-purple-600/30'
                : 'bg-slate-700/30 text-gray-400 hover:text-white'
            }`}
          >
            <span className="text-sm font-medium">{filter.label}</span>
            <span className="text-xs bg-slate-600/50 px-2 py-1 rounded-full">
              {filter.count}
            </span>
          </button>
        ))}
      </div>

      {/* Migration Progress Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6 border-b border-slate-700/50">
        <div className="bg-slate-700/30 rounded-lg p-4">
          <div className="text-sm text-gray-400 mb-1">Avg. Migration Time</div>
          <div className="text-lg font-bold text-white">6.2 hours</div>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-4">
          <div className="text-sm text-gray-400 mb-1">Success Rate</div>
          <div className="text-lg font-bold text-green-400">78.5%</div>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-4">
          <div className="text-sm text-gray-400 mb-1">Total Migrated</div>
          <div className="text-lg font-bold text-white">145</div>
        </div>
      </div>

      {/* Table Header */}
      <div className="px-6 py-3 bg-slate-700/20 border-b border-slate-700/50">
        <div className="grid grid-cols-12 gap-4 text-xs font-medium text-gray-400 uppercase tracking-wider">
          <div className="col-span-3">Token</div>
          <div className="col-span-2 text-center">Progress</div>
          <div className="col-span-2 text-center">Time Left</div>
          <div className="col-span-1 text-center">Price</div>
          <div className="col-span-2 text-center">24h Change</div>
          <div className="col-span-2 text-center">Volume 24h</div>
        </div>
      </div>

      {/* Scrollable Token Table */}
      <div className="h-96 overflow-y-auto">
        <div className="divide-y divide-slate-700/50">
          {filteredTokens.map((token, index) => (
            <div
              key={token.address}
              className={`px-6 py-4 hover:bg-slate-700/20 transition-colors ${getStatusColor(token.status)}`}
            >
              <div className="grid grid-cols-12 gap-4 items-center">
                {/* Token Info */}
                <div className="col-span-3 flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    {getStatusIcon(token.status)}
                  </div>
                  <div className="min-w-0">
                    <div className="font-medium text-white truncate">{token.name}</div>
                    <div className="text-sm text-gray-400 flex items-center space-x-2">
                      <span className="truncate">{token.symbol}</span>
                      <span>•</span>
                      <span className="font-mono text-xs">
                        {token.address.slice(0, 6)}...{token.address.slice(-4)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Migration Progress */}
                <div className="col-span-2 text-center">
                  {token.status !== 'migrated' ? (
                    <div className="flex flex-col items-center space-y-1">
                      <div className="w-full bg-slate-600 rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-purple-500 to-blue-500 rounded-full h-2 transition-all duration-300"
                          style={{ width: `${token.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-white font-medium">{token.progress.toFixed(1)}%</span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center">
                      <CheckCircle className="h-5 w-5 text-green-400" />
                    </div>
                  )}
                </div>

                {/* Time Left */}
                <div className="col-span-2 text-center">
                  <div className={`text-sm font-medium ${
                    token.status === 'migrated' ? 'text-green-400' : 'text-white'
                  }`}>
                    {token.timeLeft}
                  </div>
                </div>

                {/* Price */}
                <div className="col-span-1 text-center">
                  <div className="text-sm font-medium text-white">
                    {formatCurrency(token.currentPrice)}
                  </div>
                </div>

                {/* 24h Change */}
                <div className="col-span-2 text-center">
                  <div className={`text-sm font-medium flex items-center justify-center space-x-1 ${
                    token.change24h >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    <TrendingUp className={`h-3 w-3 ${token.change24h < 0 ? 'rotate-180' : ''}`} />
                    <span>{token.change24h >= 0 ? '+' : ''}{token.change24h.toFixed(1)}%</span>
                  </div>
                </div>

                {/* Volume */}
                <div className="col-span-2 text-center">
                  <div className="text-sm font-medium text-white">
                    {formatVolume(token.volume24h)}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="px-6 py-4 border-t border-slate-700/50 bg-slate-700/10">
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>
            Showing {filteredTokens.length} of {tokens.length} tokens
          </span>
          <span>
            Data updates every 30 seconds
          </span>
        </div>
      </div>
    </div>
  )
} 