'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Copy, ExternalLink, TrendingUp, TrendingDown, Activity, DollarSign, Calendar, User, CheckCircle, XCircle } from 'lucide-react'

interface WalletData {
  address: string
  label?: string
  totalPnl: number
  totalTrades: number
  winRate: number
  totalVolume: number
  avgTradeSize: number
  firstTradeDate: string
  lastTradeDate: string
  profitableTrades: number
  losingTrades: number
  biggestWin: number
  biggestLoss: number
  currentHoldings: any[]
  recentTrades: any[]
}

export default function WalletDetailPage() {
  const params = useParams()
  const router = useRouter()
  const address = params.address as string
  const [walletData, setWalletData] = useState<WalletData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (address) {
      fetchWalletData(address)
    }
  }, [address])

  const fetchWalletData = async (walletAddress: string) => {
    try {
      setLoading(true)
      const response = await fetch(`/api/wallet/analysis/${walletAddress}`)
      const result = await response.json()
      
      if (result.success) {
        setWalletData(result.data)
      } else {
        setError(result.error || 'Failed to fetch wallet data')
      }
    } catch (err) {
      setError('Network error occurred')
    } finally {
      setLoading(false)
    }
  }

  const copyAddress = () => {
    navigator.clipboard.writeText(address)
  }

  const openInExplorer = () => {
    window.open(`https://snowtrace.io/address/${address}`, '_blank')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0f0f23] via-[#1a1a2e] to-[#16213e] p-6">
        <div className="max-w-7xl mx-auto pt-8">
          <div className="animate-pulse">
            <div className="h-8 bg-backgroundSecondary/30 rounded w-1/3 mb-8"></div>
            <div className="grid md:grid-cols-4 gap-6 mb-8">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-32 bg-backgroundSecondary/30 rounded-2xl"></div>
              ))}
            </div>
            <div className="h-96 bg-backgroundSecondary/30 rounded-2xl"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !walletData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0f0f23] via-[#1a1a2e] to-[#16213e] p-6">
        <div className="max-w-7xl mx-auto pt-8">
          <button
            onClick={() => router.back()}
            className="flex items-center space-x-2 text-textSecondary hover:text-textPrimary mb-8 transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
            <span>Back</span>
          </button>
          <div className="text-center py-16">
            <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-textPrimary mb-2">Wallet Not Found</h2>
            <p className="text-textSecondary mb-6">{error || 'No data available for this wallet address'}</p>
            <button
              onClick={() => router.push('/intel')}
              className="px-6 py-3 bg-gradient-to-r from-primaryBlue to-primaryPurple text-white rounded-xl font-semibold hover:shadow-lg transition-all"
            >
              Back to Intel
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f0f23] via-[#1a1a2e] to-[#16213e] p-6">
      <div className="max-w-7xl mx-auto pt-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="flex items-center space-x-2 text-textSecondary hover:text-textPrimary mb-6 transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
            <span>Back to Intel</span>
          </button>

          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-2">
                <h1 className="text-3xl font-bold text-textPrimary">
                  {walletData.label || 'Unknown Wallet'}
                </h1>
                {walletData.label && (
                  <span className="px-3 py-1 bg-primaryGreen/20 text-primaryGreen text-sm rounded-lg border border-primaryGreen/30">
                    Labeled
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-textSecondary font-mono text-sm">
                  {address.substring(0, 6)}...{address.substring(address.length - 4)}
                </span>
                <button
                  onClick={copyAddress}
                  className="p-1 text-textSecondary hover:text-textPrimary transition-colors"
                  title="Copy address"
                >
                  <Copy className="h-4 w-4" />
                </button>
                <button
                  onClick={openInExplorer}
                  className="p-1 text-textSecondary hover:text-textPrimary transition-colors"
                  title="View on Snowtrace"
                >
                  <ExternalLink className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-textSecondary">Total P&L</span>
              {walletData.totalPnl >= 0 ? (
                <TrendingUp className="h-4 w-4 text-primaryGreen" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-500" />
              )}
            </div>
            <div className={`text-2xl font-bold ${walletData.totalPnl >= 0 ? 'text-primaryGreen' : 'text-red-500'}`}>
              {walletData.totalPnl >= 0 ? '+' : ''}${walletData.totalPnl.toLocaleString()}
            </div>
          </div>

          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-textSecondary">Total Trades</span>
              <Activity className="h-4 w-4 text-primaryBlue" />
            </div>
            <div className="text-2xl font-bold text-textPrimary">{walletData.totalTrades}</div>
            <div className="text-xs text-textSecondary mt-1">
              {walletData.profitableTrades}W / {walletData.losingTrades}L
            </div>
          </div>

          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-textSecondary">Win Rate</span>
              <CheckCircle className="h-4 w-4 text-primaryPurple" />
            </div>
            <div className="text-2xl font-bold text-textPrimary">{walletData.winRate.toFixed(1)}%</div>
          </div>

          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-textSecondary">Total Volume</span>
              <DollarSign className="h-4 w-4 text-primaryOrange" />
            </div>
            <div className="text-2xl font-bold text-textPrimary">${walletData.totalVolume.toLocaleString()}</div>
          </div>
        </div>

        {/* Additional Stats */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <h3 className="text-lg font-semibold text-textPrimary mb-4">Trading Summary</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-textSecondary">Average Trade Size</span>
                <span className="text-textPrimary font-medium">${walletData.avgTradeSize.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-textSecondary">Biggest Win</span>
                <span className="text-primaryGreen font-medium">+${walletData.biggestWin.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-textSecondary">Biggest Loss</span>
                <span className="text-red-500 font-medium">-${Math.abs(walletData.biggestLoss).toLocaleString()}</span>
              </div>
            </div>
          </div>

          <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
            <h3 className="text-lg font-semibold text-textPrimary mb-4">Activity Timeline</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-textSecondary">First Trade</span>
                <span className="text-textPrimary font-medium">{walletData.firstTradeDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-textSecondary">Last Trade</span>
                <span className="text-textPrimary font-medium">{walletData.lastTradeDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-textSecondary">Days Active</span>
                <span className="text-textPrimary font-medium">
                  {Math.ceil((new Date(walletData.lastTradeDate).getTime() - new Date(walletData.firstTradeDate).getTime()) / (1000 * 60 * 60 * 24))}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Trades */}
        <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
          <h3 className="text-lg font-semibold text-textPrimary mb-4">Recent Trades</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-primaryStroke/20">
                  <th className="text-left text-sm text-textSecondary py-3">Date</th>
                  <th className="text-left text-sm text-textSecondary py-3">Type</th>
                  <th className="text-left text-sm text-textSecondary py-3">Token</th>
                  <th className="text-right text-sm text-textSecondary py-3">Amount</th>
                  <th className="text-right text-sm text-textSecondary py-3">P&L</th>
                </tr>
              </thead>
              <tbody>
                {walletData.recentTrades.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center text-textSecondary py-8">
                      No recent trades found
                    </td>
                  </tr>
                ) : (
                  walletData.recentTrades.map((trade, index) => (
                    <tr key={index} className="border-b border-primaryStroke/10">
                      <td className="py-3 text-sm text-textSecondary">{trade.date}</td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          trade.type === 'BUY' 
                            ? 'bg-primaryGreen/20 text-primaryGreen' 
                            : 'bg-red-500/20 text-red-500'
                        }`}>
                          {trade.type}
                        </span>
                      </td>
                      <td className="py-3 text-sm text-textPrimary">{trade.token}</td>
                      <td className="py-3 text-sm text-textPrimary text-right">${trade.amount.toLocaleString()}</td>
                      <td className={`py-3 text-sm text-right font-medium ${
                        trade.pnl >= 0 ? 'text-primaryGreen' : 'text-red-500'
                      }`}>
                        {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
} 