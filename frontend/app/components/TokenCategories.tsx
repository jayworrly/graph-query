'use client'

import { Sparkles, Clock, CheckCircle, Copy, ExternalLink } from 'lucide-react'
import { useState } from 'react'

const newPairsData = [
  {
    name: 'Unknown Token',
    symbol: 'UNK',
    price: '$0.001000',
    marketCap: '$10000k',
    volume24h: '$0k',
    holders: 0,
    launched: '1 minutes ago',
    liquidity: '$0k',
    change: '0.0%',
    positive: true,
    address: '0x7b1...99f8'
  },
  {
    name: 'Unknown Token',
    symbol: 'UNK',
    price: '$0.001000',
    marketCap: '$10000k',
    volume24h: '$0k',
    holders: 0,
    launched: '1 minutes ago',
    liquidity: '$0k',
    change: '0.0%',
    positive: true,
    address: '0x8f4d...084d'
  }
]

const migrationData = [
  {
    name: 'BEART AT DRIVE',
    symbol: 'BEART',
    price: '$0.001000',
    marketCap: '$0k',
    volume24h: '$45k',
    holders: 0,
    migrationProgress: 94,
    timeToMigration: '10 hours',
    change: '5.9%',
    positive: true,
    address: '0xa2bd...6c90'
  },
  {
    name: 'KATAX',
    symbol: 'KATAX',
    price: '$0.001000',
    marketCap: '$0k',
    volume24h: '$56k',
    holders: 0,
    migrationProgress: 81,
    timeToMigration: '37 hours',
    change: '2.7%',
    positive: true,
    address: '0xec89...9873'
  }
]

export default function TokenCategories() {
  const [loadingStates, setLoadingStates] = useState({
    newPairs: false,
    migrations: false,
    migrated: false
  })

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
              <p className="text-sm text-gray-400">50 tokens</p>
            </div>
          </div>

          <div className="space-y-4">
            {loadingStates.newPairs ? (
              Array(2).fill(0).map((_, i) => <SkeletonCard key={i} />)
            ) : (
              newPairsData.map((token, index) => (
                <div key={index} className="bg-slate-700/50 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center">
                        <span className="text-xs text-gray-300">?</span>
                      </div>
                      <div>
                        <div className="font-medium text-white">{token.name}</div>
                        <div className="text-sm text-gray-400">{token.symbol}</div>
                      </div>
                    </div>
                    <div className={`text-sm font-medium ${token.positive ? 'text-green-400' : 'text-red-400'}`}>
                      {token.positive ? '↗' : '↘'} {token.change}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Price</div>
                      <div className="text-white font-medium">{token.price}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Market Cap</div>
                      <div className="text-white font-medium">{token.marketCap}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Volume 24h</div>
                      <div className="text-white font-medium">{token.volume24h}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Holders</div>
                      <div className="text-white font-medium">{token.holders}</div>
                    </div>
                  </div>

                  <div className="text-sm">
                    <div className="text-gray-400">Launched</div>
                    <div className="text-green-400">{token.launched}</div>
                  </div>

                  <div className="text-sm">
                    <div className="text-gray-400">Liquidity</div>
                    <div className="text-white">{token.liquidity}</div>
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
              <p className="text-sm text-gray-400">20 tokens</p>
            </div>
          </div>

          <div className="space-y-4">
            {loadingStates.migrations ? (
              Array(2).fill(0).map((_, i) => <SkeletonCard key={i} />)
            ) : (
              migrationData.map((token, index) => (
                <div key={index} className="bg-slate-700/50 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center">
                        <span className="text-xs text-gray-300">B</span>
                      </div>
                      <div>
                        <div className="font-medium text-white">{token.name}</div>
                        <div className="text-sm text-gray-400">{token.symbol}</div>
                      </div>
                    </div>
                    <div className={`text-sm font-medium ${token.positive ? 'text-green-400' : 'text-red-400'}`}>
                      {token.positive ? '↗' : '↘'} {token.change}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Price</div>
                      <div className="text-white font-medium">{token.price}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Market Cap</div>
                      <div className="text-white font-medium">{token.marketCap}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Volume 24h</div>
                      <div className="text-white font-medium">{token.volume24h}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Holders</div>
                      <div className="text-white font-medium">{token.holders}</div>
                    </div>
                  </div>

                  <div className="text-sm">
                    <div className="text-gray-400">Migration Progress</div>
                    <div className="flex items-center space-x-2 mt-1">
                      <div className="flex-1 bg-slate-600 rounded-full h-2">
                        <div 
                          className="bg-yellow-400 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${token.migrationProgress}%` }}
                        ></div>
                      </div>
                      <span className="text-yellow-400 font-medium">{token.migrationProgress}%</span>
                    </div>
                  </div>

                  <div className="text-sm">
                    <div className="text-gray-400">Time to Migration</div>
                    <div className="text-yellow-400">{token.timeToMigration}</div>
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
              <p className="text-sm text-gray-400">0 tokens</p>
            </div>
          </div>

          <div className="space-y-4">
            {loadingStates.migrated ? (
              Array(3).fill(0).map((_, i) => <SkeletonCard key={i} />)
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircle className="h-12 w-12 text-gray-500 mb-4" />
                <h4 className="text-lg font-medium text-gray-300 mb-2">No tokens found</h4>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
} 