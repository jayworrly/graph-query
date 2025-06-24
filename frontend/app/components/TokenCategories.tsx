'use client'

import { Sparkles, Clock, CheckCircle, Copy, ExternalLink } from 'lucide-react'
import { useState, useEffect } from 'react'
import { ApiService } from '../../lib/api-service'
import { priceService } from '../../lib/price-service'

interface TokenData {
  address: string
  name: string
  symbol: string
  currentPriceAvax?: number
  currentPriceUsd?: number
  marketCapAvax?: number
  marketCapUsd?: number
  avaxRaised?: number
  avaxRaisedUsd?: number
  bondingProgress?: number
  totalTrades?: number
  estimatedTimeToMigration?: number
  deployedAt?: number
  category: string
}

// Real data is now fetched from APIs

export default function TokenCategories() {
  const [loadingStates, setLoadingStates] = useState({
    newPairs: false,
    migrations: false,
    migrated: false
  })

  const [tokenData, setTokenData] = useState<{
    newPairs: TokenData[]
    migrations: TokenData[]
    migrated: TokenData[]
  }>({
    newPairs: [],
    migrations: [],
    migrated: []
  })

  // Fetch real data on component mount
  useEffect(() => {
    fetchAllTokenData()
  }, [])

  const fetchAllTokenData = async () => {
    try {
      const [newPairs, migrations, migrated] = await Promise.all([
        fetchNewPairs(),
        fetchCloseToMigration(),
        fetchMigratedTokens()
      ])

      setTokenData({
        newPairs,
        migrations,
        migrated
      })
    } catch (error) {
      console.error('Error fetching token data:', error)
    }
  }

  const fetchNewPairs = async (): Promise<TokenData[]> => {
    try {
      const response = await fetch('/api/tokens/new-pairs?limit=5')
      const result = await response.json()
      
      if (result.success && result.data?.tokens) {
        return result.data.tokens.map((token: any) => ({
          address: token.address,
          name: token.name || 'Unknown Token',
          symbol: token.symbol || 'UNK',
          currentPriceAvax: token.currentPriceAvax,
          currentPriceUsd: token.currentPriceUsd,
          marketCapAvax: token.marketCapAvax,
          marketCapUsd: token.marketCapUsd,
          totalTrades: token.totalTrades,
          deployedAt: token.deployedAt,
          category: 'new-pairs'
        }))
      }
      return []
    } catch (error) {
      console.error('Error fetching new pairs:', error)
      return []
    }
  }

  const fetchCloseToMigration = async (): Promise<TokenData[]> => {
    try {
      const response = await fetch('/api/tokens/close-to-migration?limit=5')
      const result = await response.json()
      
      if (result.success && result.data?.tokens) {
        return result.data.tokens.map((token: any) => ({
          address: token.address,
          name: token.name || 'Unknown Token',
          symbol: token.symbol || 'UNK',
          currentPriceAvax: token.currentPriceAvax,
          currentPriceUsd: token.currentPriceUsd,
          marketCapAvax: token.marketCapAvax,
          marketCapUsd: token.marketCapUsd,
          avaxRaised: token.avaxRaised,
          avaxRaisedUsd: token.avaxRaisedUsd,
          bondingProgress: token.bondingProgress,
          totalTrades: token.totalTrades,
          estimatedTimeToMigration: token.estimatedTimeToMigration,
          category: 'close-to-migration'
        }))
      }
      return []
    } catch (error) {
      console.error('Error fetching close to migration:', error)
      return []
    }
  }

  const fetchMigratedTokens = async (): Promise<TokenData[]> => {
    try {
      const response = await fetch('/api/tokens/migrated?limit=5')
      const result = await response.json()
      
      if (result.success && result.data?.tokens) {
        return result.data.tokens.map((token: any) => ({
          address: token.address,
          name: token.name || 'Unknown Token',
          symbol: token.symbol || 'UNK',
          currentPriceAvax: token.currentPriceAvax,
          currentPriceUsd: token.currentPriceUsd,
          marketCapAvax: token.marketCapAvax,
          marketCapUsd: token.marketCapUsd,
          totalTrades: token.totalTrades,
          category: 'migrated'
        }))
      }
      return []
    } catch (error) {
      console.error('Error fetching migrated tokens:', error)
      return []
    }
  }

  const toggleLoading = (category: keyof typeof loadingStates) => {
    setLoadingStates(prev => ({
      ...prev,
      [category]: !prev[category]
    }))
  }

  const SkeletonCard = () => (
    <div className="bg-slate-700/50 rounded-lg p-4 space-y-3">
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 bg-slate-600 rounded-full skeleton"></div>
        <div className="space-y-2 flex-1">
          <div className="h-4 bg-slate-600 rounded skeleton w-3/4"></div>
          <div className="h-3 bg-slate-600 rounded skeleton w-1/2"></div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="h-3 bg-slate-600 rounded skeleton"></div>
          <div className="h-4 bg-slate-600 rounded skeleton"></div>
        </div>
        <div className="space-y-2">
          <div className="h-3 bg-slate-600 rounded skeleton"></div>
          <div className="h-4 bg-slate-600 rounded skeleton"></div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="h-3 bg-slate-600 rounded skeleton"></div>
          <div className="h-4 bg-slate-600 rounded skeleton"></div>
        </div>
        <div className="space-y-2">
          <div className="h-3 bg-slate-600 rounded skeleton"></div>
          <div className="h-4 bg-slate-600 rounded skeleton"></div>
        </div>
      </div>
      <div className="h-3 bg-slate-600 rounded skeleton"></div>
      <div className="h-8 bg-slate-600 rounded skeleton"></div>
    </div>
  )

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* New Pairs */}
      <div className="space-y-6">
        <div 
          className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 cursor-pointer hover:bg-slate-800/60 transition-colors"
          onClick={() => toggleLoading('newPairs')}
        >
          <div className="flex items-center space-x-3 mb-4">
            <Sparkles className="h-6 w-6 text-green-400" />
            <div>
              <h3 className="text-lg font-semibold text-white">New Pairs</h3>
              <p className="text-sm text-gray-400">{tokenData.newPairs.length} tokens</p>
            </div>
          </div>

          <div className="space-y-4">
            {loadingStates.newPairs ? (
              Array(2).fill(0).map((_, i) => <SkeletonCard key={i} />)
            ) : tokenData.newPairs.length > 0 ? (
              tokenData.newPairs.map((token, index) => (
                <div key={index} className="bg-slate-700/50 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center">
                        <span className="text-xs text-gray-300">{token.symbol.slice(0, 2).toUpperCase()}</span>
                      </div>
                      <div>
                        <div className="font-medium text-white">{token.name}</div>
                        <div className="text-sm text-gray-400">{token.symbol}</div>
                      </div>
                    </div>
                    <div className="text-sm font-medium text-green-400">
                      ↗ New
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Price</div>
                      <div className="text-white font-medium">
                        {token.currentPriceUsd ? priceService.formatUsd(token.currentPriceUsd) : '$0.00'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400">Market Cap</div>
                      <div className="text-white font-medium">
                        {token.marketCapUsd ? priceService.formatUsd(token.marketCapUsd) : '$0'}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Trades</div>
                      <div className="text-white font-medium">{token.totalTrades || 0}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Age</div>
                      <div className="text-white font-medium">
                        {token.deployedAt ? new Date(token.deployedAt * 1000).toLocaleDateString() : 'Unknown'}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-600">
                    <code className="text-xs text-gray-400 font-mono">{token.address}</code>
                    <div className="flex space-x-2">
                      <button className="p-1 text-gray-400 hover:text-white">
                        <Copy className="h-3 w-3" />
                      </button>
                      <button className="p-1 text-gray-400 hover:text-white">
                        <ExternalLink className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-400">No new pairs found</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Close to Migrations */}
      <div className="space-y-6">
        <div 
          className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 cursor-pointer hover:bg-slate-800/60 transition-colors"
          onClick={() => toggleLoading('migrations')}
        >
          <div className="flex items-center space-x-3 mb-4">
            <Clock className="h-6 w-6 text-yellow-400" />
            <div>
              <h3 className="text-lg font-semibold text-white">Close to Migrations</h3>
              <p className="text-sm text-gray-400">{tokenData.migrations.length} tokens</p>
            </div>
          </div>

          <div className="space-y-4">
            {loadingStates.migrations ? (
              Array(2).fill(0).map((_, i) => <SkeletonCard key={i} />)
            ) : tokenData.migrations.length > 0 ? (
              tokenData.migrations.map((token, index) => (
                <div key={index} className="bg-slate-700/50 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center">
                        <span className="text-xs text-gray-300">{token.symbol.slice(0, 2).toUpperCase()}</span>
                      </div>
                      <div>
                        <div className="font-medium text-white">{token.name}</div>
                        <div className="text-sm text-gray-400">{token.symbol}</div>
                      </div>
                    </div>
                    <div className="text-sm font-medium text-yellow-400">
                      ⏳ {token.bondingProgress ? `${token.bondingProgress.toFixed(1)}%` : 'Migrating'}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Price</div>
                      <div className="text-white font-medium">
                        {token.currentPriceUsd ? priceService.formatUsd(token.currentPriceUsd) : '$0.00'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400">Market Cap</div>
                      <div className="text-white font-medium">
                        {token.marketCapUsd ? priceService.formatUsd(token.marketCapUsd) : '$0'}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">AVAX Raised</div>
                      <div className="text-white font-medium">
                        {token.avaxRaisedUsd ? priceService.formatUsd(token.avaxRaisedUsd) : '$0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400">Trades</div>
                      <div className="text-white font-medium">{token.totalTrades || 0}</div>
                    </div>
                  </div>

                  <div className="text-sm">
                    <div className="text-gray-400">Migration Progress</div>
                    <div className="flex items-center space-x-2 mt-1">
                      <div className="flex-1 bg-slate-600 rounded-full h-2">
                        <div 
                          className="bg-yellow-400 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${token.bondingProgress || 0}%` }}
                        ></div>
                      </div>
                      <span className="text-yellow-400 font-medium">{token.bondingProgress?.toFixed(1) || 0}%</span>
                    </div>
                  </div>

                  <div className="text-sm">
                    <div className="text-gray-400">Time to Migration</div>
                    <div className="text-yellow-400">
                      {token.estimatedTimeToMigration ? 
                        `~${Math.ceil(token.estimatedTimeToMigration)}h` : 
                        'Calculating...'
                      }
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-600">
                    <code className="text-xs text-gray-400 font-mono">{token.address}</code>
                    <div className="flex space-x-2">
                      <button className="p-1 text-gray-400 hover:text-white">
                        <Copy className="h-3 w-3" />
                      </button>
                      <button className="p-1 text-gray-400 hover:text-white">
                        <ExternalLink className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-400">No tokens close to migration found</p>
                <p className="text-sm text-gray-500 mt-2">Tokens need to reach 45%+ bonding progress</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Migrated */}
      <div className="space-y-6">
        <div 
          className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 cursor-pointer hover:bg-slate-800/60 transition-colors"
          onClick={() => toggleLoading('migrated')}
        >
          <div className="flex items-center space-x-3 mb-4">
            <CheckCircle className="h-6 w-6 text-blue-400" />
            <div>
              <h3 className="text-lg font-semibold text-white">Migrated</h3>
              <p className="text-sm text-gray-400">{tokenData.migrated.length} tokens</p>
            </div>
          </div>

          <div className="space-y-4">
            {loadingStates.migrated ? (
              Array(3).fill(0).map((_, i) => <SkeletonCard key={i} />)
            ) : tokenData.migrated.length > 0 ? (
              tokenData.migrated.map((token, index) => (
                <div key={index} className="bg-slate-700/50 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center">
                        <span className="text-xs text-gray-300">{token.symbol.slice(0, 2).toUpperCase()}</span>
                      </div>
                      <div>
                        <div className="font-medium text-white">{token.name}</div>
                        <div className="text-sm text-gray-400">{token.symbol}</div>
                      </div>
                    </div>
                    <div className="text-sm font-medium text-blue-400">
                      ✅ Migrated
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Price</div>
                      <div className="text-white font-medium">
                        {token.currentPriceUsd ? priceService.formatUsd(token.currentPriceUsd) : '$0.00'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400">Market Cap</div>
                      <div className="text-white font-medium">
                        {token.marketCapUsd ? priceService.formatUsd(token.marketCapUsd) : '$0'}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Trades</div>
                      <div className="text-white font-medium">{token.totalTrades || 0}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Status</div>
                      <div className="text-blue-400 font-medium">Live on DEX</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-600">
                    <code className="text-xs text-gray-400 font-mono">{token.address}</code>
                    <div className="flex space-x-2">
                      <button className="p-1 text-gray-400 hover:text-white">
                        <Copy className="h-3 w-3" />
                      </button>
                      <button className="p-1 text-gray-400 hover:text-white">
                        <ExternalLink className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircle className="h-12 w-12 text-gray-500 mb-4" />
                <h4 className="text-lg font-medium text-gray-300 mb-2">No migrated tokens found</h4>
                <p className="text-sm text-gray-500">Tokens appear here after successful migration to DEX</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
} 