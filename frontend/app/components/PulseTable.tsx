'use client'

import { useState, useEffect } from 'react'
import { Copy, ExternalLink, TrendingUp, TrendingDown, Clock, CheckCircle, Sparkles, BarChart3, Users, Zap } from 'lucide-react'
import { ApiService, type TokenData } from '../../lib/api-service'

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
    const interval = setInterval(fetchTokens, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [type])

  const fetchTokens = async () => {
    try {
      setLoading(true)
      let data: TokenData[] = []
      
      switch (type) {
        case 'new-pairs':
          data = await ApiService.getNewPairs()
          break
        case 'close-to-migration':
          data = await ApiService.getCloseToMigration()
          break
        case 'migrated':
          data = await ApiService.getMigratedTokens()
          break
      }
      
      setTokens(data.slice(0, 20)) // Show up to 20 tokens
    } catch (error) {
      console.error('Error fetching tokens:', error)
    } finally {
      setLoading(false)
    }
  }

  const getTitle = () => {
    switch (type) {
      case 'new-pairs': return 'New Pairs'
      case 'close-to-migration': return 'Close to Migration'
      case 'migrated': return 'Migrated'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'BONDING': return 'text-primaryBlue'
      case 'CLOSE_TO_MIGRATION': return 'text-primaryYellow'
      case 'MIGRATED': return 'text-primaryGreen'
      default: return 'text-textTertiary'
    }
  }

  const generateTokenIcon = (address: string) => {
    const hash = address.slice(2, 8)
    const hue = parseInt(hash, 16) % 360
    return `linear-gradient(135deg, hsl(${hue}, 70%, 60%), hsl(${(hue + 60) % 360}, 70%, 50%))`
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const openInSnowTrace = (address: string) => {
    window.open(`https://snowtrace.io/address/${address}`, '_blank')
  }

  const formatTimeAgo = (timestamp: number) => {
    const now = Date.now()
    const diff = now - timestamp * 1000
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    
    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    return `${minutes}m ago`
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toFixed(2)
  }

  const formatAvax = (num: number) => {
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    if (num >= 1) return num.toFixed(2)
    return num.toFixed(4)
  }

  const getBondingProgressColor = (progress: number) => {
    if (progress >= 90) return 'text-primaryGreen'
    if (progress >= 70) return 'text-primaryYellow'
    return 'text-primaryBlue'
  }

  const getMigrationProgressBar = (progress: number) => {
    const percentage = Math.min(progress, 100)
    let colorClass = 'bg-primaryBlue'
    if (percentage >= 90) colorClass = 'bg-primaryGreen'
    else if (percentage >= 70) colorClass = 'bg-primaryYellow'
    
    return (
      <div className="w-full h-[3px] bg-backgroundTertiary rounded-full overflow-hidden">
        <div 
          className={`h-full ${colorClass} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    )
  }

  if (loading && tokens.length === 0) {
    return (
      <div className="flex flex-col w-full h-full bg-backgroundSecondary border border-primaryStroke/50 rounded-[8px] overflow-hidden">
        {/* Header */}
        <div className="flex flex-row w-full h-[48px] px-[16px] gap-[12px] justify-between items-center border-b border-primaryStroke/50 bg-backgroundSecondary">
          <div className="flex flex-row gap-[8px] justify-start items-center">
            <div className="w-[16px] h-[16px] bg-slate-700 rounded-full animate-pulse"></div>
            <div className="h-[16px] bg-slate-700 rounded-[4px] w-[120px] animate-pulse"></div>
          </div>
          <div className="flex flex-row gap-[8px] justify-end items-center">
            <div className="w-[24px] h-[24px] bg-slate-700 rounded-[4px] animate-pulse"></div>
          </div>
        </div>

        {/* Loading Cards */}
        <div className="flex-1 p-[12px] gap-[8px] flex flex-col overflow-y-auto scrollbar-thin">
          {Array(6).fill(0).map((_, i) => (
            <div key={i} className="bg-backgroundSecondary border-primaryStroke/50 border-b-[1px] flex flex-col w-full justify-start items-center relative overflow-hidden h-[116px] min-h-[116px] animate-pulse">
              <div className="flex flex-row w-full gap-[12px] pl-[12px] pr-[16px] pt-[12px] pb-[12px] justify-start items-center">
                {/* Token Icon */}
                <div className="flex flex-col items-center gap-[4px]">
                  <div className="w-[68px] h-[68px] bg-slate-700 rounded-[1px] flex-shrink-0"></div>
                  <div className="h-[12px] bg-slate-700 rounded-[4px] w-[60px]"></div>
                </div>
                
                {/* Content */}
                <div className="flex flex-col flex-1 h-full gap-[8px] justify-start items-start pt-[4px] pb-[12px] overflow-hidden">
                  <div className="flex flex-col w-full gap-[4px] justify-start items-start min-w-0">
                    <div className="h-[18px] bg-slate-700 rounded-[4px] w-3/4"></div>
                    <div className="h-[14px] bg-slate-700 rounded-[4px] w-1/2"></div>
                  </div>
                  
                  <div className="flex flex-row w-full gap-[8px] justify-between items-center">
                    <div className="h-[14px] bg-slate-700 rounded-[4px] w-[80px]"></div>
                    <div className="h-[16px] bg-slate-700 rounded-[4px] w-[60px]"></div>
                  </div>
                  
                  <div className="flex flex-row w-full gap-[4px] justify-start items-center">
                    <div className="h-[20px] bg-slate-700 rounded-full w-[60px]"></div>
                    <div className="h-[20px] bg-slate-700 rounded-full w-[80px]"></div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col w-full h-full bg-backgroundSecondary border border-primaryStroke/50 rounded-[8px] overflow-hidden">
      {/* Header */}
      <div className="flex flex-row w-full h-[48px] px-[16px] gap-[12px] justify-between items-center border-b border-primaryStroke/50 bg-backgroundSecondary">
        <div className="flex flex-row gap-[8px] justify-start items-center">
          <div className="bg-primaryGreen/20 w-[12px] h-[12px] rounded-full flex flex-row gap-[4px] justify-center items-center">
            <div className="bg-primaryGreen w-[8px] h-[8px] rounded-full"></div>
          </div>
          <span className="text-textPrimary text-[14px] font-medium">{getTitle()}</span>
          <span className="text-textTertiary text-[12px] font-medium">({tokens.length})</span>
        </div>
        
        <div className="flex flex-row gap-[8px] justify-end items-center">
          <div className="flex items-center justify-center w-[24px] h-[24px] rounded-[4px] transition-colors duration-150 ease-in-out text-textSecondary hover:bg-primaryStroke/40 cursor-pointer">
            <i className="ri-more-line text-[14px]"></i>
          </div>
        </div>
      </div>

      {/* Token Cards */}
      <div className="flex-1 p-[12px] gap-[8px] flex flex-col overflow-y-auto scrollbar-thin">
        {tokens.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-textTertiary">
            <i className="ri-search-line text-[32px] mb-[8px] opacity-50"></i>
            <span className="text-[14px] font-medium">No tokens found</span>
          </div>
        ) : (
          tokens.map((token, index) => (
            <div
              key={token.address}
              className="bg-backgroundSecondary border-primaryStroke/50 border-b-[1px] flex flex-col w-full justify-start items-start cursor-pointer relative overflow-hidden hover:bg-primaryStroke/50 group min-h-[96px] transition-colors duration-125 ease-in-out p-[12px] gap-[8px]"
              onClick={() => openInSnowTrace(token.address)}
            >
              {/* Hide Button */}
              <div className="absolute left-[6px] top-[6px] z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-125 text-textTertiary hover:text-primaryBlueHover w-[20px] h-[20px] flex items-center justify-center rounded-[4px] bg-backgroundTertiary border border-secondaryStroke/50">
                <i className="ri-eye-off-line text-[12px]"></i>
              </div>

              {/* Top Row - Token Info and Price */}
              <div className="flex flex-row w-full justify-between items-start">
                {/* Left - Token Icon and Info */}
                <div className="flex flex-row gap-[12px] items-center flex-1 min-w-0">
                  {/* Token Icon */}
                  <div className="flex-shrink-0 relative">
                    <div className="relative w-[40px] h-[40px] justify-center items-center">
                      {/* Status Indicator */}
                      <div className={`flex absolute top-[28px] left-[28px] p-[1px] w-[12px] h-[12px] justify-center items-center rounded-full z-30 ${
                        type === 'migrated' ? 'bg-primaryGreen' : 
                        type === 'close-to-migration' ? 'bg-primaryYellow' : 'bg-primaryBlue'
                      }`}>
                        <div className="flex justify-center items-center bg-background absolute w-[10px] h-[10px] rounded-full z-30"></div>
                      </div>
                      
                      {/* Icon */}
                      <div 
                        className="rounded-[6px] w-[40px] h-[40px] flex items-center justify-center text-[14px] font-bold text-white border border-textPrimary/10"
                        style={{ background: generateTokenIcon(token.address) }}
                      >
                        {token.symbol.slice(0, 2).toUpperCase()}
                      </div>
                    </div>
                  </div>

                  {/* Token Name and Info */}
                  <div className="flex flex-col flex-1 min-w-0">
                    <div className="flex flex-row items-center gap-[8px] min-w-0">
                      <span className="text-textPrimary text-[16px] font-medium tracking-[-0.02em] truncate">
                        {token.symbol}
                      </span>
                      <span className="text-textTertiary text-[12px] font-medium truncate">
                        {token.name}
                      </span>
                      <i className="ri-file-copy-fill text-[10px] text-textTertiary hover:text-primaryBlueHover transition-colors duration-125 cursor-pointer flex-shrink-0"
                         onClick={(e) => {
                           e.stopPropagation()
                           copyToClipboard(token.symbol)
                         }}></i>
                    </div>
                    
                    {/* Time and Address */}
                    <div className="flex flex-row items-center gap-[8px] mt-[2px]">
                      <span className="text-primaryGreen text-[11px] font-medium">
                        {token.launched ? formatTimeAgo(Math.floor(token.launched.getTime() / 1000)) : 'Unknown'}
                      </span>
                      <span 
                        className="text-textTertiary text-[11px] font-medium hover:text-primaryBlueHover transition-colors duration-125 cursor-pointer"
                        onClick={(e) => {
                          e.stopPropagation()
                          copyToClipboard(token.address)
                        }}
                      >
                        {token.address.slice(0, 6)}...{token.address.slice(-4)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Right - Price and Change */}
                <div className="flex flex-col items-end justify-start">
                  <span className="text-textPrimary text-[16px] font-medium">
                    {formatAvax(token.price)} AVAX
                  </span>
                  {token.change24h !== undefined && (
                    <div className={`flex flex-row items-center gap-[4px] ${
                      token.change24h >= 0 ? 'text-primaryGreen' : 'text-red-400'
                    }`}>
                      {token.change24h >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      <span className="text-[11px] font-medium">
                        {Math.abs(token.change24h).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Middle Row - Trading Stats */}
              <div className="flex flex-row w-full justify-between items-center gap-[16px]">
                {/* Trading Statistics */}
                <div className="flex flex-row gap-[16px] items-center">
                  {/* Market Cap */}
                  <div className="flex flex-col items-start">
                    <span className="text-textTertiary text-[10px] font-medium uppercase tracking-wide">MC</span>
                    <span className="text-textPrimary text-[13px] font-medium">
                      ${formatNumber(token.marketCap || 0)}
                    </span>
                  </div>

                  {/* Volume 24h */}
                  <div className="flex flex-col items-start">
                    <span className="text-textTertiary text-[10px] font-medium uppercase tracking-wide">Vol 24h</span>
                    <span className="text-textPrimary text-[13px] font-medium">
                      {formatAvax(token.volume24h || 0)} AVAX
                    </span>
                  </div>

                  {/* Trades */}
                  {token.totalTrades !== undefined && (
                    <div className="flex flex-col items-start">
                      <span className="text-textTertiary text-[10px] font-medium uppercase tracking-wide">Trades</span>
                      <div className="flex flex-row items-center gap-[4px]">
                        <BarChart3 size={12} className="text-textSecondary" />
                        <span className="text-textPrimary text-[13px] font-medium">
                          {formatNumber(token.totalTrades)}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Traders */}
                  {token.uniqueTraders !== undefined && (
                    <div className="flex flex-col items-start">
                      <span className="text-textTertiary text-[10px] font-medium uppercase tracking-wide">Traders</span>
                      <div className="flex flex-row items-center gap-[4px]">
                        <Users size={12} className="text-textSecondary" />
                        <span className="text-textPrimary text-[13px] font-medium">
                          {formatNumber(token.uniqueTraders)}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Quick Buy Button */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-125 flex-shrink-0">
                  <div className="bg-primaryBlue hover:bg-primaryBlueHover text-white flex flex-row gap-[4px] justify-center items-center rounded-[6px] h-[28px] px-[12px] whitespace-nowrap transition-all duration-125 relative overflow-hidden">
                    <Zap size={12} className="flex items-center relative z-10" />
                    <span className="text-[11px] font-bold relative z-10">BUY</span>
                  </div>
                </div>
              </div>

              {/* Bottom Row - Progress Bar and Migration Info */}
              {type === 'close-to-migration' && token.migrationProgress !== undefined && (
                <div className="flex flex-col w-full gap-[4px]">
                  <div className="flex flex-row justify-between items-center">
                    <span className="text-textTertiary text-[10px] font-medium uppercase tracking-wide">
                      Migration Progress
                    </span>
                    <div className="flex flex-row items-center gap-[4px]">
                      <span className={`text-[11px] font-medium ${getBondingProgressColor(token.migrationProgress)}`}>
                        {token.migrationProgress.toFixed(1)}%
                      </span>
                      {token.avaxRaised !== undefined && token.migrationThreshold !== undefined && (
                        <span className="text-textTertiary text-[10px] font-medium">
                          ({formatAvax(token.avaxRaised)}/{formatAvax(token.migrationThreshold)} AVAX)
                        </span>
                      )}
                    </div>
                  </div>
                  {getMigrationProgressBar(token.migrationProgress)}
                  {token.timeToMigration && (
                    <span className="text-primaryYellow text-[10px] font-medium">
                      Est. {token.timeToMigration} to migration
                    </span>
                  )}
                </div>
              )}

              {/* Migrated Token Info */}
              {type === 'migrated' && (
                <div className="flex flex-row w-full justify-between items-center">
                  <div className="flex flex-row items-center gap-[4px]">
                    <CheckCircle size={12} className="text-primaryGreen" />
                    <span className="text-primaryGreen text-[11px] font-medium">
                      Migrated {token.migrationDate || 'Recently'}
                    </span>
                  </div>
                  {token.liquidity !== undefined && (
                    <span className="text-textTertiary text-[11px] font-medium">
                      Liquidity: {formatAvax(token.liquidity)} AVAX
                    </span>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
} 