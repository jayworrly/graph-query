'use client'

import PulseTable from '../components/PulseTable'

export default function Explore() {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background">
      {/* Header - Fixed with Axiom Trade styling */}
      <div className="flex-shrink-0 border-b border-primaryStroke overflow-hidden flex flex-row w-full h-[64px] px-[24px] justify-between sm:justify-start items-center">
        <div className="flex flex-row flex-shrink-0 gap-[12px] justify-start items-center">
          <div className="flex flex-col gap-[2px] justify-start items-start">
            <h1 className="text-textPrimary text-[18px] font-medium tracking-[-0.02em]">
              Explore Tokens
            </h1>
            <p className="text-textTertiary text-[12px] font-medium">
              Discover new pairs, track migrations, and explore opportunities
            </p>
          </div>
        </div>
        
        <div className="flex flex-row gap-[12px] justify-end items-center">
          {/* Refresh Button */}
          <div className="flex items-center justify-center w-[32px] h-[32px] rounded-[4px] transition-colors duration-150 ease-in-out text-textSecondary hover:bg-primaryStroke/40 cursor-pointer">
            <i className="ri-refresh-line text-[16px]"></i>
          </div>
          
          {/* Settings Button */}
          <div className="flex items-center justify-center w-[32px] h-[32px] rounded-[4px] transition-colors duration-150 ease-in-out text-textSecondary hover:bg-primaryStroke/40 cursor-pointer">
            <i className="ri-settings-3-line text-[16px]"></i>
          </div>
        </div>
      </div>

      {/* Tables Grid - Scrollable Content */}
      <div className="flex-1 p-[12px] min-h-0 overflow-hidden">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-[12px] h-full">
          <div className="min-h-0 flex flex-col">
            <PulseTable type="new-pairs" />
          </div>
          <div className="min-h-0 flex flex-col">
            <PulseTable type="close-to-migration" />
          </div>
          <div className="min-h-0 flex flex-col">
            <PulseTable type="migrated" />
          </div>
        </div>
      </div>
    </div>
  )
} 