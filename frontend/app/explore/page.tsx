'use client'

import PulseTable from '../components/PulseTable'

export default function Explore() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">
            Explore Tokens
          </h1>
          <p className="text-gray-400">
            Discover new pairs, track migrations, and explore token opportunities
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-slate-800/50 rounded-lg px-3 py-2">
            <input
              type="text"
              placeholder="Search tokens..."
              className="bg-transparent text-sm text-white placeholder-gray-400 border-none outline-none w-48"
            />
          </div>
          <button className="p-2 text-gray-400 hover:text-purple-400 transition-colors">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* All Three Tables in Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="space-y-4">
          <PulseTable type="new-pairs" />
        </div>
        <div className="space-y-4">
          <PulseTable type="close-to-migration" />
        </div>
        <div className="space-y-4">
          <PulseTable type="migrated" />
        </div>
      </div>
    </div>
  )
} 