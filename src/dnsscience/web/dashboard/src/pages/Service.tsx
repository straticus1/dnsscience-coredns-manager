import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Square, RotateCcw, RefreshCw } from 'lucide-react'
import { getServiceStatus, startService, stopService, restartService, reloadService } from '../api'
import { useStore } from '../store'

export default function Service() {
  const { resolver } = useStore()
  const queryClient = useQueryClient()

  const { data: status, isLoading } = useQuery({
    queryKey: ['service-status', resolver],
    queryFn: () => getServiceStatus(),
    refetchInterval: 5000,
  })

  const startMutation = useMutation({
    mutationFn: startService,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['service-status'] }),
  })

  const stopMutation = useMutation({
    mutationFn: stopService,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['service-status'] }),
  })

  const restartMutation = useMutation({
    mutationFn: restartService,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['service-status'] }),
  })

  const reloadMutation = useMutation({
    mutationFn: reloadService,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['service-status'] }),
  })

  const isRunning = status?.data?.state === 'running'

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Service Management</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Card */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Service Status</h2>

          {isLoading ? (
            <p>Loading...</p>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div
                  className={`w-4 h-4 rounded-full ${
                    isRunning ? 'bg-green-400' : 'bg-red-400'
                  }`}
                />
                <span className="text-2xl font-bold">
                  {status?.data?.state?.toUpperCase() || 'UNKNOWN'}
                </span>
              </div>

              <table className="w-full text-sm">
                <tbody className="divide-y divide-gray-700">
                  <tr>
                    <td className="py-2 text-gray-400">Resolver</td>
                    <td className="py-2 text-right">{resolver.toUpperCase()}</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-400">Version</td>
                    <td className="py-2 text-right font-mono">
                      {status?.data?.version || 'Unknown'}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-400">Config Path</td>
                    <td className="py-2 text-right font-mono text-xs">
                      {status?.data?.config_path || 'Unknown'}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-400">Listening</td>
                    <td className="py-2 text-right font-mono">
                      {status?.data?.listening_addresses?.join(', ') || 'None'}
                    </td>
                  </tr>
                  {status?.data?.uptime_seconds && (
                    <tr>
                      <td className="py-2 text-gray-400">Uptime</td>
                      <td className="py-2 text-right">
                        {Math.floor(status.data.uptime_seconds / 3600)}h{' '}
                        {Math.floor((status.data.uptime_seconds % 3600) / 60)}m
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Controls Card */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Service Control</h2>

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending || isRunning}
              className="btn btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              Start
            </button>

            <button
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending || !isRunning}
              className="btn btn-danger flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Square className="w-4 h-4" />
              Stop
            </button>

            <button
              onClick={() => restartMutation.mutate()}
              disabled={restartMutation.isPending}
              className="btn btn-secondary flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <RotateCcw className="w-4 h-4" />
              Restart
            </button>

            <button
              onClick={() => reloadMutation.mutate()}
              disabled={reloadMutation.isPending || !isRunning}
              className="btn btn-secondary flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4" />
              Reload
            </button>
          </div>

          {(startMutation.isError || stopMutation.isError || restartMutation.isError || reloadMutation.isError) && (
            <div className="mt-4 p-3 bg-red-900/20 border border-red-800 rounded-lg text-red-400">
              Operation failed. Please try again.
            </div>
          )}

          {(startMutation.isSuccess || stopMutation.isSuccess || restartMutation.isSuccess || reloadMutation.isSuccess) && (
            <div className="mt-4 p-3 bg-green-900/20 border border-green-800 rounded-lg text-green-400">
              Operation completed successfully.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
