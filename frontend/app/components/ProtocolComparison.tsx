'use client'

import { BarChart, ExternalLink, TrendingUp, Users, Zap } from 'lucide-react'
import { useState, useEffect } from 'react'

interface Protocol {
  name: string
  chain: string
  tvl: number
  volume24h: number
  fees24h: number
  users24h: number
  launches24h: number
  change24h: number
  marketShare: number
}

export default function ProtocolComparison() {
  const [protocols, setProtocols] = useState<Protocol[]>([])
  const [sortBy, setSortBy] = useState<'tvl' | 'volume24h' | 'launches24h'>('tvl')

  useEffect(() => {
    const fetchProtocolData = async () => {
      try {
        const response = await fetch(`/api/tokens/protocol-comparison?sortBy=${sortBy}`)
        const data = await response.json()
        
        if (data.success) {
          const protocolData = data.data.protocols.map((p: any) => ({
            name: p.name,
            chain: p.chain,
            tvl: p.tvl,
            volume24h: p.volume24h,
            fees24h: p.volume24h * 0.03, // 3% fee estimate
            users24h: Math.floor(p.launches24h * 15), // Rough estimate
            launches24h: p.launches24h,
            change24h: p.change24h,
            marketShare: (p.tvl / data.data.marketStats.totalTVL) * 100
          }))
          
          setProtocols(protocolData)
        }
      } catch (error) {
        console.error('Error fetching protocol data:', error)
        setProtocols([])
      }
    }

    fetchProtocolData()
    const interval = setInterval(fetchProtocolData, 300000) // Update every 5 minutes
    
    return () => clearInterval(interval)
  }, [sortBy])

  const formatCurrency = (value: number | undefined) => {
    const numValue = Number(value) || 0
    if (numValue >= 1000000) {
      return `$${(numValue / 1000000).toFixed(1)}M`
    }
    if (numValue >= 1000) {
      return `$${(numValue / 1000).toFixed(0)}K`
    }
    return `$${numValue.toFixed(0)}`
  }

  const formatNumber = (value: number) => {
    return value.toLocaleString()
  }

  const getChainIcon = (chain: string) => {
    // Return appropriate chain icons/colors
    const chainColors: { [key: string]: string } = {
      'Avalanche': 'text-red-400',
      'Solana': 'text-purple-400',
      'Tron': 'text-red-500',
      'Base': 'text-blue-400',
      'Blast': 'text-yellow-400'
    }
    return chainColors[chain] || 'text-gray-400'
  }

  const sortOptions = [
    { key: 'tvl' as const, label: 'TVL' },
    { key: 'volume24h' as const, label: '24h Volume' },
    { key: 'launches24h' as const, label: 'Launches' }
  ]

  return (
    <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <BarChart className="h-5 w-5 text-blue-400" />
          <h3 className="text-xl font-semibold text-white">Protocol Rankings</h3>
        </div>
        
        {/* Sort Dropdown */}
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as 'tvl' | 'volume24h' | 'launches24h')}
          className="bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-1 text-sm text-white focus:outline-none focus:border-purple-500"
        >
          {sortOptions.map((option) => (
            <option key={option.key} value={option.key}>
              Sort by {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Arena Highlight */}
      <div className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 border border-purple-500/30 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
            <div>
              <div className="font-semibold text-white">Arena (You are here)</div>
              <div className="text-sm text-gray-300">Rank #{protocols.findIndex(p => p.name === 'Arena') + 1} on Avalanche</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-white">{formatCurrency(protocols.find(p => p.name === 'Arena')?.tvl || 0)}</div>
            <div className="text-sm text-green-400">+15.2% 24h</div>
          </div>
        </div>
      </div>

      {/* Protocol List */}
      <div className="space-y-3">
        {protocols.map((protocol, index) => (
          <div
            key={protocol.name}
            className={`flex items-center justify-between p-4 rounded-lg border transition-colors ${
              protocol.name === 'Arena'
                ? 'bg-purple-600/10 border-purple-500/30 hover:bg-purple-600/20'
                : 'bg-slate-700/20 border-slate-600/30 hover:bg-slate-700/30'
            }`}
          >
            {/* Rank and Protocol Info */}
            <div className="flex items-center space-x-4">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm ${
                index === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                index === 1 ? 'bg-gray-400/20 text-gray-300' :
                index === 2 ? 'bg-orange-500/20 text-orange-400' :
                'bg-slate-600/20 text-slate-400'
              }`}>
                {index + 1}
              </div>
              
              <div className="flex items-center space-x-3">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-white">{protocol.name}</span>
                    {protocol.name === 'Arena' && (
                      <span className="px-2 py-1 bg-purple-600/20 text-purple-400 text-xs rounded-full">
                        YOU
                      </span>
                    )}
                  </div>
                  <div className={`text-sm ${getChainIcon(protocol.chain)}`}>
                    {protocol.chain}
                  </div>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-4 gap-6 text-right">
              {/* TVL */}
              <div>
                <div className="text-sm text-gray-400 mb-1">TVL</div>
                <div className="text-sm font-medium text-white">
                  {formatCurrency(protocol.tvl)}
                </div>
              </div>

              {/* Volume */}
              <div>
                <div className="text-sm text-gray-400 mb-1">Volume 24h</div>
                <div className="text-sm font-medium text-white">
                  {formatCurrency(protocol.volume24h)}
                </div>
              </div>

              {/* Launches */}
              <div>
                <div className="text-sm text-gray-400 mb-1">Launches 24h</div>
                <div className="text-sm font-medium text-white flex items-center justify-end space-x-1">
                  <Zap className="h-3 w-3" />
                  <span>{protocol.launches24h}</span>
                </div>
              </div>

              {/* Change */}
              <div>
                <div className="text-sm text-gray-400 mb-1">24h Change</div>
                <div className={`text-sm font-medium flex items-center justify-end space-x-1 ${
                  protocol.change24h >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  <TrendingUp className={`h-3 w-3 ${protocol.change24h < 0 ? 'rotate-180' : ''}`} />
                  <span>{protocol.change24h >= 0 ? '+' : ''}{protocol.change24h.toFixed(1)}%</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Market Analysis */}
      <div className="mt-6 pt-4 border-t border-slate-700/50">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-700/30 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Users className="h-4 w-4 text-blue-400" />
              <span className="text-sm font-medium text-white">Total Market</span>
            </div>
            <div className="text-lg font-bold text-white">
              {formatCurrency(protocols.reduce((sum, p) => sum + p.tvl, 0))}
            </div>
            <div className="text-xs text-gray-400">Combined TVL</div>
          </div>
          
          <div className="bg-slate-700/30 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <TrendingUp className="h-4 w-4 text-green-400" />
              <span className="text-sm font-medium text-white">Arena Share</span>
            </div>
            <div className="text-lg font-bold text-white">
              {protocols.find(p => p.name === 'Arena')?.marketShare.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-400">Of total market</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
        <span>Data aggregated from multiple sources</span>
        <span>Updated: Just now</span>
      </div>
    </div>
  )
} 