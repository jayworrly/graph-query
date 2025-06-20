'use client'

import { TrendingUp, Activity, BarChart3, Coins } from 'lucide-react'
import { useEffect, useState } from 'react'

interface ArenaStats {
  totalValueLocked: number
  totalVolume24h: number
  activeTokens: number
  totalMigrations: number
  change24h: number
}

export default function ArenaOverview() {
  const [stats, setStats] = useState<ArenaStats>({
    totalValueLocked: 0,
    totalVolume24h: 0,
    activeTokens: 0,
    totalMigrations: 0,
    change24h: 0
  })

  const [protocolBreakdown, setProtocolBreakdown] = useState({
    tokenFactory: { value: 0, percentage: 0, change24h: 0 },
    bondingCurves: { value: 0, percentage: 0, change24h: 0 },
    dexLiquidity: { value: 0, percentage: 0, change24h: 0 }
  })

  const [activeTab, setActiveTab] = useState<'tvl' | 'volume' | 'migrations' | 'activity'>('tvl')

  useEffect(() => {
    const fetchArenaData = async () => {
      try {
        const response = await fetch('/api/tokens/overview')
        const data = await response.json()
        
        if (data.success) {
          setStats({
            totalValueLocked: data.data.totalValueLocked,
            totalVolume24h: data.data.volume24h,
            activeTokens: data.data.activeTokens,
            totalMigrations: data.data.totalMigrations,
            change24h: data.data.change24h
          })
          
          setProtocolBreakdown(data.data.protocolBreakdown)
        }
      } catch (error) {
        console.error('Error fetching Arena data:', error)
      }
    }

    fetchArenaData()
    const interval = setInterval(fetchArenaData, 30000) // Update every 30 seconds
    
    return () => clearInterval(interval)
  }, [])

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">
          Arena Protocol Analytics
        </h1>
        <p className="text-gray-400 text-lg">
          Comprehensive analytics for the Arena token launching ecosystem on Avalanche
        </p>
      </div>

      {/* Main TVL Display */}
      <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="text-sm text-gray-400 mb-2">Total Value Locked in Arena</div>
            <div className="flex items-center space-x-4">
              <div className="text-5xl font-bold text-white">
                {formatCurrency(stats.totalValueLocked)}
              </div>
              <div className="flex items-center space-x-2 text-green-400">
                <TrendingUp className="h-5 w-5" />
                <span className="text-lg font-medium">+{stats.change24h}%</span>
                <span className="text-sm text-gray-400">24h</span>
              </div>
            </div>
          </div>
          
          {/* Tab Navigation */}
          <div className="flex space-x-2 bg-slate-700/50 rounded-lg p-1">
            {[
              { key: 'tvl' as const, label: 'TVL', icon: BarChart3 },
              { key: 'volume' as const, label: 'Volume', icon: Activity },
              { key: 'migrations' as const, label: 'Migrations', icon: TrendingUp },
              { key: 'activity' as const, label: 'Activity', icon: Coins }
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-slate-600/50'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-white mb-1">
              {formatCurrency(stats.totalVolume24h)}
            </div>
            <div className="text-sm text-gray-400">Volume (24h)</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-white mb-1">
              {formatNumber(stats.activeTokens)}
            </div>
            <div className="text-sm text-gray-400">Active Tokens</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-white mb-1">
              {formatNumber(stats.totalMigrations)}
            </div>
            <div className="text-sm text-gray-400">Total Migrations</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-white mb-1">
              78.5%
            </div>
            <div className="text-sm text-gray-400">Success Rate</div>
          </div>
        </div>
      </div>

      {/* Protocol Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Arena Token Factory</h3>
            <div className="text-sm text-green-400">+{protocolBreakdown.tokenFactory.change24h}%</div>
          </div>
          <div className="text-2xl font-bold text-white mb-2">
            {formatCurrency(protocolBreakdown.tokenFactory.value)}
          </div>
          <div className="text-sm text-gray-400">
            {protocolBreakdown.tokenFactory.percentage}% of total TVL
          </div>
        </div>

        <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Bonding Curves</h3>
            <div className="text-sm text-green-400">+{protocolBreakdown.bondingCurves.change24h}%</div>
          </div>
          <div className="text-2xl font-bold text-white mb-2">
            {formatCurrency(protocolBreakdown.bondingCurves.value)}
          </div>
          <div className="text-sm text-gray-400">
            {protocolBreakdown.bondingCurves.percentage}% of total TVL
          </div>
        </div>

        <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">DEX Liquidity</h3>
            <div className="text-sm text-green-400">+{protocolBreakdown.dexLiquidity.change24h}%</div>
          </div>
          <div className="text-2xl font-bold text-white mb-2">
            {formatCurrency(protocolBreakdown.dexLiquidity.value)}
          </div>
          <div className="text-sm text-gray-400">
            {protocolBreakdown.dexLiquidity.percentage}% of total TVL
          </div>
        </div>
      </div>
    </div>
  )
} 