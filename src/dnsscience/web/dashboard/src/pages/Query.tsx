import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { dnsQuery } from '../api'

const RECORD_TYPES = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA', 'PTR', 'SRV']

export default function Query() {
  const [domain, setDomain] = useState('')
  const [recordType, setRecordType] = useState('A')
  const [dnssec, setDnssec] = useState(false)

  const queryMutation = useMutation({
    mutationFn: () => dnsQuery({ name: domain, record_type: recordType, dnssec }),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (domain) {
      queryMutation.mutate()
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">DNS Query</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Query Form */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">DNS Lookup</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
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
                {RECORD_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="dnssec"
                checked={dnssec}
                onChange={(e) => setDnssec(e.target.checked)}
                className="rounded"
              />
              <label htmlFor="dnssec" className="text-sm text-gray-400">
                DNSSEC Validation
              </label>
            </div>

            <button
              type="submit"
              disabled={!domain || queryMutation.isPending}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <Search className="w-4 h-4" />
              {queryMutation.isPending ? 'Querying...' : 'Query'}
            </button>
          </form>
        </div>

        {/* Results */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Results</h2>

          {queryMutation.isPending && (
            <p className="text-gray-400">Loading...</p>
          )}

          {queryMutation.isError && (
            <div className="p-3 bg-red-900/20 border border-red-800 rounded-lg text-red-400">
              Query failed. Please try again.
            </div>
          )}

          {queryMutation.isSuccess && queryMutation.data?.data && (
            <div className="space-y-4">
              {/* Response Code */}
              <div className="flex items-center gap-2">
                <span className="text-gray-400">RCODE:</span>
                <span
                  className={`font-mono ${
                    queryMutation.data.data.rcode === 'NOERROR'
                      ? 'text-green-400'
                      : 'text-red-400'
                  }`}
                >
                  {queryMutation.data.data.rcode}
                </span>
              </div>

              {/* Records */}
              {queryMutation.data.data.records?.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-400 border-b border-gray-700">
                      <th className="py-2 text-left">Name</th>
                      <th className="py-2 text-left">Type</th>
                      <th className="py-2 text-left">TTL</th>
                      <th className="py-2 text-left">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {queryMutation.data.data.records.map((record: any, i: number) => (
                      <tr key={i}>
                        <td className="py-2 font-mono text-xs">{record.name}</td>
                        <td className="py-2">{record.record_type}</td>
                        <td className="py-2">{record.ttl}s</td>
                        <td className="py-2 font-mono text-xs break-all">
                          {record.value}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-gray-400">No records found</p>
              )}

              {/* Metadata */}
              <div className="pt-4 border-t border-gray-700 text-sm text-gray-400">
                <p>Server: {queryMutation.data.data.server}</p>
                <p>Time: {queryMutation.data.data.query_time_ms?.toFixed(2)}ms</p>
                {dnssec && (
                  <p>
                    DNSSEC:{' '}
                    {queryMutation.data.data.dnssec_valid === true
                      ? '✓ Valid'
                      : queryMutation.data.data.dnssec_valid === false
                      ? '✗ Invalid'
                      : 'Not validated'}
                  </p>
                )}
              </div>
            </div>
          )}

          {!queryMutation.isPending && !queryMutation.isSuccess && !queryMutation.isError && (
            <p className="text-gray-400">Enter a domain to query</p>
          )}
        </div>
      </div>
    </div>
  )
}
