import StatsCards from './components/StatsCards'
import VolumeChart from './components/VolumeChart'
import TopPerformers from './components/TopPerformers'

export default function Dashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">
          Ballistic Terminal Launcher
        </h1>
        <p className="text-gray-400">
          High-velocity token launches and analytics on Avalanche
        </p>
      </div>

      {/* Stats Cards */}
      <StatsCards />

      {/* Charts and Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <VolumeChart />
        </div>
        <div>
          <TopPerformers />
        </div>
      </div>
    </div>
  )
} 