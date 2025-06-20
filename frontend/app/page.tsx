import StatsCards from './components/StatsCards'
import VolumeChart from './components/VolumeChart'
import TopPerformers from './components/TopPerformers'
import ArenaOverview from './components/ArenaOverview'
import TokenLaunchMetrics from './components/TokenLaunchMetrics'
import MigrationTracker from './components/MigrationTracker'
import ProtocolComparison from './components/ProtocolComparison'

export default function Dashboard() {
  return (
    <div className="space-y-8">
      {/* Arena Overview - Main TVL/Volume Stats */}
      <ArenaOverview />

      {/* Key Metrics Grid - Now handled by ArenaOverview component */}

      {/* Main Chart Section */}
      <TokenLaunchMetrics />

      {/* Data Sections Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - 2/3 width */}
        <div className="lg:col-span-2 space-y-8">
          <VolumeChart />
          <MigrationTracker />
        </div>
        
        {/* Right Column - 1/3 width */}
        <div className="space-y-8">
          <TopPerformers />
          <ProtocolComparison />
        </div>
      </div>
    </div>
  )
} 