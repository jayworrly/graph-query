'use client'

import { useState, useEffect } from 'react'
import { Copy, ExternalLink, TrendingUp, TrendingDown, Clock, CheckCircle, Sparkles } from 'lucide-react'
import { blockchainService, type TokenData } from '../../lib/blockchain.service'

interface PulseTableProps {
  type: 'new-pairs' | 'close-to-migration' | 'migrated'
}

export default function PulseTable({ type }: PulseTableProps) {
  const [tokens, setTokens] = useState<TokenData[]>([])
  const [loading, setLoading] = useState(false)
  const [sortField, setSortField] = useState<string>('launched')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    fetchTokens()
    const interval = setInterval(fetchTokens, 15000) // Refresh every 15 seconds
    return () => clearInterval(interval)
  }, [type])

  const fetchTokens = async () => {
    setLoading(true)
    try {
      let data: TokenData[] = []
      
      switch (type) {
        case 'new-pairs':
          data = await blockchainService.getNewPairs(50)
          break
        case 'close-to-migration':
          data = await blockchainService.getCloseToMigration(20)
          break
        case 'migrated':
          data = await blockchainService.getMigratedTokens(20)
          break
      }
      
      setTokens(data)
    } catch (error) {
      console.error('Error fetching tokens:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSort = (field: string) => {
    const direction = sortField === field && sortDirection === 'desc' ? 'asc' : 'desc'
    setSortField(field)
    setSortDirection(direction)
  }

  const formatPrice = (price?: number) => {
    if (!price) return '$0.000000'
    if (price < 0.000001) return price.toExponential(2)
    return `$${price.toFixed(6)}`
  }

  const formatMarketCap = (marketCap?: number) => {
    if (!marketCap) return '$0'
    if (marketCap >= 1000000) return `$${(marketCap / 1000000).toFixed(1)}M`
    if (marketCap >= 1000) return `$${(marketCap / 1000).toFixed(0)}K`
    return `$${marketCap.toFixed(0)}`
  }

  const formatVolume = (volume?: number) => {
    if (!volume) return '$0'
    if (volume >= 1000000) return `$${(volume / 1000000).toFixed(1)}M`
    if (volume >= 1000) return `$${(volume / 1000).toFixed(0)}K`
    return `$${volume.toFixed(0)}`
  }

  const getTimeAgo = (date?: Date) => {
    if (!date) return 'Unknown'
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)
    
    if (days > 0) return `${days}d`
    if (hours > 0) return `${hours}h`
    return `${minutes}m`
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const getTableTitle = () => {
    switch (type) {
      case 'new-pairs': return { title: 'New Pairs', icon: Sparkles, count: tokens.length, color: 'text-green-400' }
      case 'close-to-migration': return { title: 'Close to Migration', icon: Clock, count: tokens.length, color: 'text-yellow-400' }
      case 'migrated': return { title: 'Migrated Tokens', icon: CheckCircle, count: tokens.length, color: 'text-purple-400' }
    }
  }

  const tableInfo = getTableTitle()
  const Icon = tableInfo.icon

  if (loading && tokens.length === 0) {
    return (
      <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center space-x-3 mb-6">
          <Icon className={`h-5 w-5 ${tableInfo.color}`} />
          <h3 className="text-lg font-semibold text-white">{tableInfo.title}</h3>
          <div className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <div className="space-y-4">
          {Array(5).fill(0).map((_, i) => (
            <div key={i} className="h-16 bg-slate-700/30 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    )
  }

  if (tokens.length === 0) {
    return (
      <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center space-x-3 mb-6">
          <Icon className={`h-5 w-5 ${tableInfo.color}`} />
          <h3 className="text-lg font-semibold text-white">{tableInfo.title}</h3>
          <span className="text-sm text-gray-400">({tableInfo.count} tokens)</span>
        </div>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Icon className="h-12 w-12 text-gray-500 mb-4" />
          <h4 className="text-lg font-medium text-gray-300 mb-2">No tokens found</h4>
          <p className="text-sm text-gray-500">
            {type === 'migrated' ? 'Tokens will appear here after migrating to DEX trading.' : 'New tokens will appear here soon.'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Icon className={`h-5 w-5 ${tableInfo.color}`} />
          <h3 className="text-lg font-semibold text-white">{tableInfo.title}</h3>
          <span className="text-sm text-gray-400">({tableInfo.count} tokens)</span>
        </div>
        <button
          onClick={fetchTokens}
          disabled={loading}
          className="px-3 py-1 text-xs bg-purple-600/20 text-purple-400 rounded-lg hover:bg-purple-600/30 transition-colors disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-600/50">
              <th className="text-left py-3 px-2 font-medium text-gray-400">#</th>
              <th className="text-left py-3 px-2 font-medium text-gray-400">Token</th>
              <th 
                className="text-right py-3 px-2 font-medium text-gray-400 cursor-pointer hover:text-white"
                onClick={() => handleSort('price')}
              >
                Price
              </th>
              <th 
                className="text-right py-3 px-2 font-medium text-gray-400 cursor-pointer hover:text-white"
                onClick={() => handleSort('marketCap')}
              >
                Market Cap
              </th>
              <th 
                className="text-right py-3 px-2 font-medium text-gray-400 cursor-pointer hover:text-white"
                onClick={() => handleSort('volume24h')}
              >
                24h Volume
              </th>
              {type === 'close-to-migration' && (
                <th className="text-center py-3 px-2 font-medium text-gray-400">Progress</th>
              )}
              <th className="text-right py-3 px-2 font-medium text-gray-400">
                {type === 'new-pairs' ? 'Launched' : type === 'close-to-migration' ? 'Time Left' : 'Migrated'}
              </th>
              <th className="text-center py-3 px-2 font-medium text-gray-400">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((token, index) => (
              <tr 
                key={token.address} 
                className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors"
              >
                <td className="py-4 px-2 text-gray-400">{index + 1}</td>
                <td className="py-4 px-2">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-purple-400 to-purple-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                      {token.symbol?.charAt(0) || '?'}
                    </div>
                    <div>
                      <div className="font-medium text-white">{token.name}</div>
                      <div className="text-xs text-gray-400">{token.symbol}</div>
                    </div>
                  </div>
                </td>
                <td className="py-4 px-2 text-right text-white font-mono">
                  {formatPrice(token.price)}
                </td>
                <td className="py-4 px-2 text-right text-white">
                  {formatMarketCap(token.marketCap)}
                </td>
                <td className="py-4 px-2 text-right text-white">
                  {formatVolume(token.volume24h)}
                </td>
                {type === 'close-to-migration' && (
                  <td className="py-4 px-2">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-slate-600 rounded-full h-2">
                        <div 
                          className="bg-yellow-400 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${token.migrationProgress || 0}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-yellow-400 font-medium min-w-[40px]">
                        {token.migrationProgress || 0}%
                      </span>
                    </div>
                  </td>
                )}
                <td className="py-4 px-2 text-right">
                  {type === 'new-pairs' && (
                    <span className="text-green-400 text-xs">
                      {getTimeAgo(token.launched)} ago
                    </span>
                  )}
                  {type === 'close-to-migration' && (
                    <span className="text-yellow-400 text-xs">
                      {token.timeToMigration}
                    </span>
                  )}
                  {type === 'migrated' && (
                    <span className="text-purple-400 text-xs">
                      {getTimeAgo(token.launched)} ago
                    </span>
                  )}
                </td>
                <td className="py-4 px-2">
                  <div className="flex items-center justify-center space-x-2">
                    <button
                      onClick={() => copyToClipboard(token.address)}
                      className="p-1 text-gray-400 hover:text-white transition-colors"
                      title="Copy address"
                    >
                      <Copy className="h-3 w-3" />
                    </button>
                    <button
                      onClick={() => window.open(`https://snowtrace.io/address/${token.address}`, '_blank')}
                      className="p-1 text-gray-400 hover:text-white transition-colors"
                      title="View on SnowTrace"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
} 