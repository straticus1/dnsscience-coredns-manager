import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { GitCompare } from 'lucide-react'
import { compareSingle, compareBulk } from '../api'

export default function Compare() {
  const [domain, setDomain] = useState('')
  const [recordType, setRecordType] = useState('A')
  const [bulkDomains, setBulkDomains] = useState('')

  const singleMutation = useMutation({
    mutationFn: () => compareSingle(domain, recordType),
  })

  const bulkMutation = useMutation({
    mutationFn: () => {
      const domains = bulkDomains.split('\n').map(d => d.trim()).filter(d => d)
      return compareBulk(domains, recordType)
    },
  })

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Resolver Comparison</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Single Compare */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Compare Single Query</h2>

          <form
            onSubmit={(e) => {
              e.preventDefault()
              singleMutation.mutate()
            }}
            className="space-y-4"
          >
            <div>
              <label className="block text-sm text-gray-400 mb-1">Domain</label>
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="example.com"
                className="input w-full"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Record Type</label>
              <select
                value={recordType}
                onChange={(e) => setRecordType(e.target.value)}
                className="select w-full"
              >
                <option value="A">A</option>
                <option value="AAAA">AAAA</option>
                <option value="MX">MX</option>
                <option value="NS">NS</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={!domain || singleMutation.isPending}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <GitCompare className="w-4 h-4" />
              Compare
            </button>
          </form>

          {singleMutation.isSuccess && singleMutation.data?.data && (
            <div className="mt-4">
              <div
                className={`p-3 rounded-lg ${
                  singleMutation.data.data.match
                    ? 'bg-green-900/20 border border-green-800 text-green-400'
                    : 'bg-red-900/20 border border-red-800 text-red-400'
                }`}
              >
                {singleMutation.data.data.match ? '✓ Responses Match' : '✗ Responses Differ'}
              </div>

              <div className="mt-4 space-y-2 text-sm">
                <p>Source RCODE: {singleMutation.data.data.source_response?.rcode}</p>
                <p>Target RCODE: {singleMutation.data.data.target_response?.rcode}</p>
                <p>
                  Timing Diff: {singleMutation.data.data.timing_diff_ms?.toFixed(2)}ms
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Bulk Compare */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Bulk Comparison</h2>

          <form
            onSubmit={(e) => {
              e.preventDefault()
              bulkMutation.mutate()
            }}
            className="space-y-4"
          >
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Domains (one per line)
              </label>
              <textarea
                value={bulkDomains}
                onChange={(e) => setBulkDomains(e.target.value)}
                placeholder="google.com&#10;cloudflare.com&#10;github.com"
                rows={6}
                className="input w-full font-mono text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={!bulkDomains || bulkMutation.isPending}
              className="btn btn-primary w-full"
            >
              {bulkMutation.isPending ? 'Comparing...' : 'Run Bulk Comparison'}
            </button>
          </form>

          {bulkMutation.isSuccess && bulkMutation.data?.data && (
            <div className="mt-4 space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold">
                    {bulkMutation.data.data.queries_tested}
                  </p>
                  <p className="text-sm text-gray-400">Tested</p>
                </div>
                <div className="bg-green-900/20 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-green-400">
                    {bulkMutation.data.data.matches}
                  </p>
                  <p className="text-sm text-gray-400">Matches</p>
                </div>
                <div className="bg-red-900/20 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-red-400">
                    {bulkMutation.data.data.mismatches}
                  </p>
                  <p className="text-sm text-gray-400">Mismatches</p>
                </div>
              </div>

              <div className="bg-gray-700/50 rounded-lg p-4">
                <p className="text-lg font-semibold mb-2">
                  Confidence Score:{' '}
                  <span
                    className={
                      bulkMutation.data.data.confidence_score >= 0.95
                        ? 'text-green-400'
                        : bulkMutation.data.data.confidence_score >= 0.9
                        ? 'text-yellow-400'
                        : 'text-red-400'
                    }
                  >
                    {(bulkMutation.data.data.confidence_score * 100).toFixed(1)}%
                  </span>
                </p>
                <p className="text-sm text-gray-400">
                  {bulkMutation.data.data.confidence_score >= 0.99
                    ? 'Ready for migration'
                    : bulkMutation.data.data.confidence_score >= 0.95
                    ? 'Review mismatches before migrating'
                    : 'Not recommended for migration'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
