import { useQuery } from '@tanstack/react-query'
import { Activity, Database, Server, Zap } from 'lucide-react'
import { getServiceStatus, getCacheStats, getHealth } from '../api'
import { useStore } from '../store'

export default function Dashboard() {
  const { resolver } = useStore()

  const { data: status } = useQuery({
    queryKey: ['service-status', resolver],
    queryFn: () => getServiceStatus(),
  })

  const { data: cache } = useQuery({
    queryKey: ['cache-stats', resolver],
    queryFn: () => getCacheStats(),
  })

  const { data: health } = useQuery({
    queryKey: ['health', resolver],
    queryFn: () => getHealth(),
  })

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Service Status"
          value={status?.data?.state || 'Unknown'}
          icon={Server}
          color={status?.data?.state === 'running' ? 'green' : 'red'}
        />
        <StatCard
          title="Health"
          value={health?.data?.state || 'Unknown'}
          icon={Activity}
          color={health?.data?.state === 'healthy' ? 'green' : 'yellow'}
        />
        <StatCard
          title="Cache Entries"
          value={cache?.data?.size?.toLocaleString() || '0'}
          icon={Database}
          color="blue"
        />
        <StatCard
          title="Hit Ratio"
          value={`${((cache?.data?.hit_ratio || 0) * 100).toFixed(1)}%`}
          icon={Zap}
          color="purple"
        />
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Service Details */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Service Details</h2>
          <table className="w-full">
            <tbody className="divide-y divide-gray-700">
              <TableRow label="Resolver" value={resolver.toUpperCase()} />
              <TableRow label="State" value={status?.data?.state || 'Unknown'} />
              <TableRow label="Version" value={status?.data?.version || 'Unknown'} />
              <TableRow label="Config" value={status?.data?.config_path || 'Unknown'} />
              <TableRow
                label="Listening"
                value={status?.data?.listening_addresses?.join(', ') || 'None'}
              />
            </tbody>
          </table>
        </div>

        {/* Cache Details */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Cache Statistics</h2>
          <table className="w-full">
            <tbody className="divide-y divide-gray-700">
              <TableRow label="Entries" value={cache?.data?.size?.toLocaleString() || '0'} />
              <TableRow label="Hits" value={cache?.data?.hits?.toLocaleString() || '0'} />
              <TableRow label="Misses" value={cache?.data?.misses?.toLocaleString() || '0'} />
              <TableRow
                label="Hit Ratio"
                value={`${((cache?.data?.hit_ratio || 0) * 100).toFixed(1)}%`}
              />
              <TableRow
                label="Evictions"
                value={cache?.data?.evictions?.toLocaleString() || '0'}
              />
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

interface StatCardProps {
  title: string
  value: string
  icon: React.ComponentType<{ className?: string }>
  color: 'green' | 'red' | 'yellow' | 'blue' | 'purple'
}

function StatCard({ title, value, icon: Icon, color }: StatCardProps) {
  const colorClasses = {
    green: 'bg-green-900/20 text-green-400 border-green-800',
    red: 'bg-red-900/20 text-red-400 border-red-800',
    yellow: 'bg-yellow-900/20 text-yellow-400 border-yellow-800',
    blue: 'bg-blue-900/20 text-blue-400 border-blue-800',
    purple: 'bg-purple-900/20 text-purple-400 border-purple-800',
  }

  return (
    <div className={`rounded-lg border p-6 ${colorClasses[color]}`}>
      <div className="flex items-center gap-4">
        <Icon className="w-8 h-8" />
        <div>
          <p className="text-sm opacity-80">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </div>
  )
}

function TableRow({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td className="py-2 text-gray-400">{label}</td>
      <td className="py-2 text-right font-mono">{value}</td>
    </tr>
  )
}
