import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, RefreshCw } from 'lucide-react'
import { getCacheStats, flushCache, purgeDomain } from '../api'
import { useStore } from '../store'

export default function Cache() {
  const { resolver } = useStore()
  const queryClient = useQueryClient()
  const [domain, setDomain] = useState('')

  const { data: stats, isLoading } = useQuery({
    queryKey: ['cache-stats', resolver],
    queryFn: () => getCacheStats(),
    refetchInterval: 10000,
  })

  const flushMutation = useMutation({
    mutationFn: flushCache,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cache-stats'] }),
  })

  const purgeMutation = useMutation({
    mutationFn: (domain: string) => purgeDomain(domain),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cache-stats'] })
      setDomain('')
    },
  })

  const handlePurge = (e: React.FormEvent) => {
    e.preventDefault()
    if (domain) {
      purgeMutation.mutate(domain)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Cache Management</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stats */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Cache Statistics</h2>
            <button
              onClick={() => queryClient.invalidateQueries({ queryKey: ['cache-stats'] })}
              className="btn btn-secondary btn-sm p-2"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {isLoading ? (
            <p>Loading...</p>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <StatBox label="Entries" value={stats?.data?.size?.toLocaleString() || '0'} />
                <StatBox
                  label="Hit Ratio"
                  value={`${((stats?.data?.hit_ratio || 0) * 100).toFixed(1)}%`}
                />
                <StatBox label="Hits" value={stats?.data?.hits?.toLocaleString() || '0'} />
                <StatBox label="Misses" value={stats?.data?.misses?.toLocaleString() || '0'} />
              </div>

              <button
                onClick={() => {
                  if (confirm('Are you sure you want to flush the entire cache?')) {
                    flushMutation.mutate()
                  }
                }}
                disabled={flushMutation.isPending}
                className="btn btn-danger w-full flex items-center justify-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                {flushMutation.isPending ? 'Flushing...' : 'Flush All Cache'}
              </button>

              {flushMutation.isSuccess && (
                <div className="p-3 bg-green-900/20 border border-green-800 rounded-lg text-green-400">
                  Cache flushed successfully
                </div>
              )}
            </div>
          )}
        </div>

        {/* Purge Domain */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Purge Domain</h2>

          <form onSubmit={handlePurge} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Domain to Purge</label>
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="example.com"
                className="input w-full"
              />
            </div>

            <button
              type="submit"
              disabled={!domain || purgeMutation.isPending}
              className="btn btn-primary w-full"
            >
              {purgeMutation.isPending ? 'Purging...' : 'Purge from Cache'}
            </button>
          </form>

          {purgeMutation.isSuccess && (
            <div className="mt-4 p-3 bg-green-900/20 border border-green-800 rounded-lg text-green-400">
              Domain purged successfully
            </div>
          )}

          {purgeMutation.isError && (
            <div className="mt-4 p-3 bg-red-900/20 border border-red-800 rounded-lg text-red-400">
              Failed to purge domain
            </div>
          )}

          <div className="mt-6 p-4 bg-gray-700/50 rounded-lg">
            <p className="text-sm text-gray-400">
              <strong>Note:</strong> CoreDNS does not support selective cache purge natively.
              Consider flushing the entire cache or using Unbound for granular control.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-700/50 rounded-lg p-4">
      <p className="text-sm text-gray-400">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  )
}
