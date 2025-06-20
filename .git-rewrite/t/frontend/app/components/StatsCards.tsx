'use client'

import { TrendingUp, DollarSign, Activity, Target } from 'lucide-react'
import { useEffect, useState } from 'react'
import { blockchainService } from '../../lib/blockchain.service'

export default function StatsCards() {
  const [stats, setStats] = useState([
    {
      title: 'Total Tokens',
      value: '0',
      change: '+0%',
      icon: TrendingUp,
      positive: true
    },
    {
      title: 'Total Volume',
      value: '$0',
      change: '+0%',
      icon: DollarSign,
      positive: true
    },
    {
      title: 'Active Deployments',
      value: '0',
      change: '+0',
      icon: Activity,
      positive: true
    },
    {
      title: 'Success Rate',
      value: '0.0%',
      change: '+0%',
      icon: Target,
      positive: true
    }
  ])

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await blockchainService.getOverviewStats()
        
        setStats([
          {
            title: 'Total Tokens',
            value: data.totalTokens.toString(),
            change: '+12%',
            icon: TrendingUp,
            positive: true
          },
          {
            title: 'Total Volume',
            value: `$${(data.totalVolume / 1000).toFixed(0)}K`,
            change: '+8.2%',
            icon: DollarSign,
            positive: true
          },
          {
            title: 'Active Deployments',
            value: data.activeDeployments.toString(),
            change: '+5',
            icon: Activity,
            positive: true
          },
          {
            title: 'Success Rate',
            value: `${data.successRate.toFixed(1)}%`,
            change: '+2.1%',
            icon: Target,
            positive: true
          }
        ])
      } catch (error) {
        console.error('Error fetching stats:', error)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 30000) // Update every 30 seconds
    
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat, index) => (
        <div
          key={index}
          className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 hover:bg-slate-800/60 transition-colors"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <stat.icon className="h-6 w-6 text-purple-400" />
            </div>
            <div className={`flex items-center space-x-1 text-sm font-medium ${
              stat.positive ? 'text-green-400' : 'text-red-400'
            }`}>
              <TrendingUp className="h-4 w-4" />
              <span>{stat.change}</span>
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white mb-1">
              {stat.value}
            </div>
            <div className="text-sm text-gray-400">
              {stat.title}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
} 