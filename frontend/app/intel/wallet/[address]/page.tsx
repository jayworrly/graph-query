// FILE: Enhanced Wallet Detail Page (page.tsx)
'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Copy, ExternalLink, TrendingUp, TrendingDown, Activity, DollarSign, Calendar, User, CheckCircle, XCircle, BarChart3, Zap, Shuffle } from 'lucide-react'

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

interface ParaSwapWalletData {
  address: string
  label?: string
  totalTrades: number
  buyTrades: number
  sellTrades: number
  buyPercentage: number
  uniqueTokens: number
  uniqueTransactions: number
  firstBlock: number
  lastBlock: number
  firstTradeDate: string
  lastTradeDate: string
  mostTradedToken: string
  mostTradedCount: number
  recentTrades: any[]
  topTokens: any[]
}

export default function WalletDetailPage() {
  const params = useParams()
  const router = useRouter()
  const address = params.address as string
  const [walletData, setWalletData] = useState<WalletData | null>(null)
  const [paraswapData, setParaswapData] = useState<ParaSwapWalletData | null>(null)
  const [loading, setLoading] = useState(true)
  const [paraswapLoading, setParaswapLoading] = useState(true)
  const [error, setError] = useState('')
  const [paraswapError, setParaswapError] = useState('')
  const [activeTab, setActiveTab] = useState<'bonding' | 'paraswap'>('bonding')

  useEffect(() => {
    if (address) {
      fetchWalletData(address)
      fetchParaswapData(address)
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

  const fetchParaswapData = async (walletAddress: string) => {
    try {
      setParaswapLoading(true)
      const response = await fetch(`/api/paraswap/${walletAddress}`)
      const result = await response.json()
      
      if (result.success) {
        setParaswapData(result.data)
      } else {
        setParaswapError(result.error || 'No ParaSwap data found')
      }
    } catch (err) {
      setParaswapError('Network error occurred')
    } finally {
      setParaswapLoading(false)
    }
  }

  const copyAddress = () => {
    navigator.clipboard.writeText(address)
  }

  const openInExplorer = () => {
    window.open(`https://snowtrace.io/address/${address}`, '_blank')
  }

  // Determine which tab to show by default based on available data
  useEffect(() => {
    if (!loading && !paraswapLoading) {
      if (walletData && !paraswapData) {
        setActiveTab('bonding')
      } else if (!walletData && paraswapData) {
        setActiveTab('paraswap')
      }
    }
  }, [loading, paraswapLoading, walletData, paraswapData])

  if (loading && paraswapLoading) {
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

  if (error && paraswapError) {
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
            <p className="text-textSecondary mb-6">No data available for this wallet address on bonding curves or ParaSwap</p>
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
                  {(walletData?.label || paraswapData?.label) || 'Unknown Wallet'}
                </h1>
                {(walletData?.label || paraswapData?.label) && (
                  <span className="px-3 py-1 bg-primaryGreen/20 text-primaryGreen text-sm rounded-lg border border-primaryGreen/30">
                    Labeled
                  </span>
                )}
                {/* Activity Indicators */}
                <div className="flex space-x-2">
                  {walletData && (
                    <span className="px-2 py-1 bg-primaryGreen/20 text-primaryGreen text-xs rounded border border-primaryGreen/30">
                      Bonding Active
                    </span>
                  )}
                  {paraswapData && (
                    <span className="px-2 py-1 bg-primaryBlue/20 text-primaryBlue text-xs rounded border border-primaryBlue/30">
                      ParaSwap Active
                    </span>
                  )}
                </div>
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

        {/* Tab Selector */}
        <div className="flex justify-center mb-8">
          <div className="flex bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-xl p-1">
            <button
              onClick={() => setActiveTab('bonding')}
              disabled={!walletData}
              className={`px-6 py-3 rounded-lg transition-all flex items-center space-x-2 ${
                activeTab === 'bonding' && walletData
                  ? 'bg-primaryGreen/20 text-primaryGreen border border-primaryGreen/30'
                  : !walletData
                  ? 'text-textSecondary/50 cursor-not-allowed'
                  : 'text-textSecondary hover:text-textPrimary'
              }`}
            >
              <BarChart3 className="h-4 w-4" />
              <span>Bonding Curves</span>
              {walletData && <span className="text-xs">({walletData.totalTrades})</span>}
            </button>
            <button
              onClick={() => setActiveTab('paraswap')}
              disabled={!paraswapData}
              className={`px-6 py-3 rounded-lg transition-all flex items-center space-x-2 ${
                activeTab === 'paraswap' && paraswapData
                  ? 'bg-primaryBlue/20 text-primaryBlue border border-primaryBlue/30'
                  : !paraswapData
                  ? 'text-textSecondary/50 cursor-not-allowed'
                  : 'text-textSecondary hover:text-textPrimary'
              }`}
            >
              <Zap className="h-4 w-4" />
              <span>ParaSwap DEX</span>
              {paraswapData && <span className="text-xs">({paraswapData.totalTrades})</span>}
            </button>
          </div>
        </div>

        {/* Content Based on Active Tab */}
        {activeTab === 'bonding' && walletData ? (
          // Bonding Curve Content
          <>
            {/* Bonding Stats Grid */}
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
                <div className={`text-2xl font-bold ${(walletData.totalPnl || 0) >= 0 ? 'text-primaryGreen' : 'text-red-500'}`}>
                  {(walletData.totalPnl || 0) >= 0 ? '+' : ''}${(walletData.totalPnl || 0).toLocaleString()}
                </div>
              </div>

              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-textSecondary">Total Trades</span>
                  <Activity className="h-4 w-4 text-primaryBlue" />
                </div>
                <div className="text-2xl font-bold text-textPrimary">{walletData.totalTrades || 0}</div>
                <div className="text-xs text-textSecondary mt-1">
                  {walletData.profitableTrades || 0}W / {walletData.losingTrades || 0}L
                </div>
              </div>

              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-textSecondary">Win Rate</span>
                  <CheckCircle className="h-4 w-4 text-primaryPurple" />
                </div>
                <div className="text-2xl font-bold text-textPrimary">{(walletData.winRate || 0).toFixed(1)}%</div>
              </div>

              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-textSecondary">Total Volume</span>
                  <DollarSign className="h-4 w-4 text-primaryOrange" />
                </div>
                <div className="text-2xl font-bold text-textPrimary">${(walletData.totalVolume || 0).toLocaleString()}</div>
              </div>
            </div>

            {/* Bonding Additional Stats */}
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-textPrimary mb-4">Trading Summary</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-textSecondary">Average Trade Size</span>
                    <span className="text-textPrimary font-medium">${(walletData.avgTradeSize || 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-textSecondary">Biggest Win</span>
                    <span className="text-primaryGreen font-medium">+${(walletData.biggestWin || 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-textSecondary">Biggest Loss</span>
                    <span className="text-red-500 font-medium">-${Math.abs(walletData.biggestLoss || 0).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-textPrimary mb-4">Activity Timeline</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-textSecondary">First Trade</span>
                    <span className="text-textPrimary font-medium">{walletData.firstTradeDate || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-textSecondary">Last Trade</span>
                    <span className="text-textPrimary font-medium">{walletData.lastTradeDate || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-textSecondary">Days Active</span>
                    <span className="text-textPrimary font-medium">
                      {walletData.firstTradeDate && walletData.lastTradeDate ? 
                        Math.ceil((new Date(walletData.lastTradeDate).getTime() - new Date(walletData.firstTradeDate).getTime()) / (1000 * 60 * 60 * 24)) : 
                        0
                      }
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Bonding Recent Trades */}
            <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
              <h3 className="text-lg font-semibold text-textPrimary mb-4">Recent Bonding Curve Trades</h3>
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
                          <td className="py-3 text-sm text-textPrimary text-right">${(trade.amount || 0).toLocaleString()}</td>
                          <td className={`py-3 text-sm text-right font-medium ${
                            (trade.pnl || 0) >= 0 ? 'text-primaryGreen' : 'text-red-500'
                          }`}>
                            {(trade.pnl || 0) >= 0 ? '+' : ''}${(trade.pnl || 0).toLocaleString()}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : activeTab === 'paraswap' && paraswapData ? (
          // ParaSwap Content
          <>
            {/* ParaSwap Stats Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-textSecondary">Total Trades</span>
                  <Activity className="h-4 w-4 text-primaryBlue" />
                </div>
                <div className="text-2xl font-bold text-textPrimary">{paraswapData.totalTrades || 0}</div>
                <div className="text-xs text-textSecondary mt-1">
                  {paraswapData.buyTrades || 0}B / {paraswapData.sellTrades || 0}S
                </div>
              </div>

              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-textSecondary">Buy Ratio</span>
                  <TrendingUp className="h-4 w-4 text-primaryGreen" />
                </div>
                <div className="text-2xl font-bold text-textPrimary">{(paraswapData.buyPercentage || 0).toFixed(1)}%</div>
              </div>

              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-textSecondary">Unique Tokens</span>
                  <Shuffle className="h-4 w-4 text-primaryPurple" />
                </div>
                <div className="text-2xl font-bold text-textPrimary">{paraswapData.uniqueTokens || 0}</div>
              </div>

              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-textSecondary">Transactions</span>
                  <DollarSign className="h-4 w-4 text-primaryOrange" />
                </div>
                <div className="text-2xl font-bold text-textPrimary">{paraswapData.uniqueTransactions || 0}</div>
              </div>
            </div>

            {/* ParaSwap Additional Stats */}
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-textPrimary mb-4">ParaSwap Activity</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-textSecondary">Most Traded Token</span>
                    <span className="text-textPrimary font-medium font-mono text-sm">
                      {paraswapData.mostTradedToken ? 
                        `${paraswapData.mostTradedToken.substring(0, 6)}...${paraswapData.mostTradedToken.substring(paraswapData.mostTradedToken.length - 4)}` : 
                        'N/A'
                      }
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-textSecondary">Times Traded</span>
                    <span className="text-textPrimary font-medium">{paraswapData.mostTradedCount || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-textSecondary">Block Range</span>
                    <span className="text-textPrimary font-medium">{((paraswapData.lastBlock || 0) - (paraswapData.firstBlock || 0)).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-textPrimary mb-4">Timeline</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-textSecondary">First Trade</span>
                    <span className="text-textPrimary font-medium">{paraswapData.firstTradeDate || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-textSecondary">Last Trade</span>
                    <span className="text-textPrimary font-medium">{paraswapData.lastTradeDate || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-textSecondary">First Block</span>
                    <span className="text-textPrimary font-medium">{(paraswapData.firstBlock || 0).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Top Tokens Traded */}
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-textPrimary mb-4">Top Tokens Traded</h3>
                <div className="space-y-3">
                  {paraswapData.topTokens.slice(0, 5).map((token, index) => (
                    <div key={index} className="flex justify-between items-center">
                      <div>
                        <span className="text-textPrimary font-mono text-sm">
                          {token.address.substring(0, 6)}...{token.address.substring(token.address.length - 4)}
                        </span>
                        <div className="text-xs text-textSecondary">
                          {token.buys}B / {token.sells}S
                        </div>
                      </div>
                      <span className="text-textPrimary font-medium">{token.tradeCount || 0}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-textPrimary mb-4">Trading Pattern</h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-textSecondary">Buy Trades</span>
                      <span className="text-primaryGreen">{paraswapData.buyTrades || 0}</span>
                    </div>
                    <div className="w-full bg-backgroundTertiary rounded-full h-2">
                      <div 
                        className="bg-primaryGreen h-2 rounded-full" 
                        style={{ width: `${paraswapData.buyPercentage || 0}%` }}
                      ></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-textSecondary">Sell Trades</span>
                      <span className="text-red-500">{paraswapData.sellTrades || 0}</span>
                    </div>
                    <div className="w-full bg-backgroundTertiary rounded-full h-2">
                      <div 
                        className="bg-red-500 h-2 rounded-full" 
                        style={{ width: `${100 - (paraswapData.buyPercentage || 0)}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* ParaSwap Recent Trades */}
            <div className="bg-backgroundSecondary/30 border border-primaryStroke/20 rounded-2xl p-6 backdrop-blur-sm">
              <h3 className="text-lg font-semibold text-textPrimary mb-4">Recent ParaSwap Trades</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-primaryStroke/20">
                      <th className="text-left text-sm text-textSecondary py-3">Date</th>
                      <th className="text-left text-sm text-textSecondary py-3">Type</th>
                      <th className="text-left text-sm text-textSecondary py-3">Token</th>
                      <th className="text-left text-sm text-textSecondary py-3">Amount</th>
                      <th className="text-left text-sm text-textSecondary py-3">Block</th>
                      <th className="text-left text-sm text-textSecondary py-3">Tx</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paraswapData.recentTrades.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="text-center text-textSecondary py-8">
                          No recent ParaSwap trades found
                        </td>
                      </tr>
                    ) : (
                      paraswapData.recentTrades.map((trade, index) => (
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
                          <td className="py-3 text-sm text-textPrimary font-mono">
                            {trade.tokenAddress.substring(0, 6)}...{trade.tokenAddress.substring(trade.tokenAddress.length - 4)}
                          </td>
                          <td className="py-3 text-sm text-textPrimary">{trade.amount}</td>
                          <td className="py-3 text-sm text-textSecondary">{(trade.blockNumber || 0).toLocaleString()}</td>
                          <td className="py-3 text-sm text-textSecondary font-mono">
                            <a 
                              href={`https://snowtrace.io/tx/${trade.txHash}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="hover:text-primaryBlue transition-colors"
                            >
                              {trade.txHash.substring(0, 6)}...
                            </a>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : (
          // No Data State
          <div className="text-center py-16">
            <XCircle className="h-16 w-16 text-textSecondary mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-textPrimary mb-2">No Data Available</h2>
            <p className="text-textSecondary mb-6">
              {activeTab === 'bonding' ? 'No bonding curve trading data found for this wallet' : 'No ParaSwap trading data found for this wallet'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}