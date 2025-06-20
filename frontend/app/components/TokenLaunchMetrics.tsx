'use client'

import { BarChart3, TrendingUp, Zap, Target, Calendar } from 'lucide-react'
import { useState, useEffect } from 'react'

interface ChartData {
  date: string
  tvl: number
  volume: number
  launches: number
  migrations: number
}

export default function TokenLaunchMetrics() {
  const [activeMetric, setActiveMetric] = useState<'tvl' | 'volume' | 'launches' | 'migrations'>('tvl')
  const [timeRange, setTimeRange] = useState<'1d' | '7d' | '30d' | '90d'>('7d')
  const [chartData, setChartData] = useState<ChartData[]>([])

  // Fetch real data from Arena subgraph
  useEffect(() => {
    const fetchChartData = async () => {
      try {
        const response = await fetch(`/api/tokens/metrics?timeRange=${timeRange}&metric=${activeMetric}`)
        const data = await response.json()
        
        if (data.success && data.data.metrics) {
          // Convert metrics data to chart format
          const metricData = data.data.metrics[activeMetric]?.data || []
          const formattedData = metricData.map((item: any) => ({
            date: item.date,
            tvl: data.data.metrics.tvl?.data?.find((d: any) => d.date === item.date)?.value || 0,
            volume: data.data.metrics.volume?.data?.find((d: any) => d.date === item.date)?.value || 0,
            launches: data.data.metrics.launches?.data?.find((d: any) => d.date === item.date)?.value || 0,
            migrations: data.data.metrics.migrations?.data?.find((d: any) => d.date === item.date)?.value || 0
          }))
          setChartData(formattedData)
        }
      } catch (error) {
        console.error('Error fetching chart data:', error)
        // Fallback to empty array
        setChartData([])
      }
    }

    fetchChartData()
  }, [timeRange, activeMetric])

  const formatValue = (value: number | undefined, metric: string) => {
    const numValue = Number(value) || 0
    if (metric === 'tvl' || metric === 'volume') {
      return numValue >= 1000000 ? `$${(numValue / 1000000).toFixed(1)}M` : `$${(numValue / 1000).toFixed(0)}K`
    }
    return numValue.toString()
  }

  const getCurrentValue = () => {
    if (chartData.length === 0) return 0
    const latest = chartData[chartData.length - 1]
    return latest[activeMetric]
  }

  const getChange = () => {
    if (chartData.length < 2) return 0
    const latest = chartData[chartData.length - 1]
    const previous = chartData[chartData.length - 2]
    const change = ((latest[activeMetric] - previous[activeMetric]) / previous[activeMetric]) * 100
    return change
  }

  const metrics = [
    { key: 'tvl' as const, label: 'TVL', icon: BarChart3, color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
    { key: 'volume' as const, label: 'Volume', icon: TrendingUp, color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
    { key: 'launches' as const, label: 'Launches', icon: Zap, color: 'text-green-400', bgColor: 'bg-green-500/20' },
    { key: 'migrations' as const, label: 'Migrations', icon: Target, color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' }
  ]

  const timeRanges = [
    { key: '1d' as const, label: '1D' },
    { key: '7d' as const, label: '7D' },
    { key: '30d' as const, label: '30D' },
    { key: '90d' as const, label: '3M' }
  ]

  return (
    <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Calendar className="h-5 w-5 text-gray-400" />
            <h3 className="text-xl font-semibold text-white">Arena Metrics</h3>
          </div>
          
          {/* Current Value Display */}
          <div className="flex items-center space-x-4">
            <div className="text-2xl font-bold text-white">
              {formatValue(getCurrentValue(), activeMetric)}
            </div>
            <div className={`text-sm ${getChange() >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {getChange() >= 0 ? '+' : ''}{getChange().toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="flex space-x-1 bg-slate-700/50 rounded-lg p-1">
          {timeRanges.map((range) => (
            <button
              key={range.key}
              onClick={() => setTimeRange(range.key)}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                timeRange === range.key
                  ? 'bg-slate-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* Metric Selector */}
      <div className="flex space-x-2 mb-6">
        {metrics.map((metric) => (
          <button
            key={metric.key}
            onClick={() => setActiveMetric(metric.key)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
              activeMetric === metric.key
                ? `${metric.bgColor} ${metric.color} border border-current/30`
                : 'bg-slate-700/30 text-gray-400 hover:text-white'
            }`}
          >
            <metric.icon className="h-4 w-4" />
            <span className="text-sm font-medium">{metric.label}</span>
          </button>
        ))}
      </div>

      {/* Chart Area */}
      <div className="h-80 bg-slate-900/50 rounded-lg p-6 relative overflow-hidden">
        {/* Background Grid */}
        <div className="absolute inset-0 opacity-10">
          <div className="h-full w-full" style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px'
          }} />
        </div>

        {/* Chart Visualization */}
        <div className="relative h-full flex items-end justify-between space-x-2">
          {chartData.map((data, index) => {
            const value = data[activeMetric]
            const maxValue = Math.max(...chartData.map(d => d[activeMetric]))
            const height = (value / maxValue) * 100
            const metric = metrics.find(m => m.key === activeMetric)
            
            return (
              <div
                key={index}
                className="flex-1 flex flex-col items-center group"
              >
                {/* Bar */}
                <div
                  className={`w-full ${metric?.bgColor} rounded-t-sm transition-all duration-300 group-hover:opacity-80`}
                  style={{ height: `${height}%` }}
                />
                
                {/* Date Label */}
                <div className="text-xs text-gray-500 mt-2 rotate-45 origin-left">
                  {new Date(data.date).toLocaleDateString('en-US', { 
                    month: 'short', 
                    day: 'numeric' 
                  })}
                </div>

                {/* Tooltip on Hover */}
                <div className="absolute -top-16 left-1/2 transform -translate-x-1/2 bg-slate-800 border border-slate-600 rounded-lg p-3 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                  <div className="text-sm text-white font-medium">
                    {formatValue(value, activeMetric)}
                  </div>
                  <div className="text-xs text-gray-400">
                    {new Date(data.date).toLocaleDateString()}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Y-axis Labels */}
        <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-500 -ml-12">
          {[100, 75, 50, 25, 0].map((percent) => {
            const maxValue = Math.max(...chartData.map(d => d[activeMetric]))
            const value = (maxValue * percent) / 100
            return (
              <div key={percent}>
                {formatValue(value, activeMetric)}
              </div>
            )
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-center space-x-6 text-sm text-gray-400">
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded ${metrics.find(m => m.key === activeMetric)?.bgColor}`} />
          <span>Arena {metrics.find(m => m.key === activeMetric)?.label}</span>
        </div>
        <div>Last updated: Just now</div>
      </div>
    </div>
  )
} 