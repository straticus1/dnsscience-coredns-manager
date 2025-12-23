import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ArrowRightLeft, FileCode, CheckCircle } from 'lucide-react'
import { createMigrationPlan, convertConfig, validateMigration } from '../api'

export default function Migrate() {
  const [source, setSource] = useState('coredns')
  const [target, setTarget] = useState('unbound')
  const [config, setConfig] = useState('')
  const [validationDomains, setValidationDomains] = useState('')

  const planMutation = useMutation({
    mutationFn: () => createMigrationPlan(source, target, config),
  })

  const convertMutation = useMutation({
    mutationFn: () => convertConfig(source, target, config),
  })

  const validateMutation = useMutation({
    mutationFn: () => {
      const domains = validationDomains
        ? validationDomains.split('\n').map(d => d.trim()).filter(d => d)
        : undefined
      return validateMigration(domains)
    },
  })

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">DNS Resolver Migration</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Migration Plan */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Generate Migration Plan</h2>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Source</label>
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="select w-full"
                >
                  <option value="coredns">CoreDNS</option>
                  <option value="unbound">Unbound</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Target</label>
                <select
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  className="select w-full"
                >
                  <option value="unbound">Unbound</option>
                  <option value="coredns">CoreDNS</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Source Configuration
              </label>
              <textarea
                value={config}
                onChange={(e) => setConfig(e.target.value)}
                placeholder="Paste source configuration here..."
                rows={10}
                className="input w-full font-mono text-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => planMutation.mutate()}
                disabled={!config || planMutation.isPending}
                className="btn btn-primary flex items-center justify-center gap-2"
              >
                <ArrowRightLeft className="w-4 h-4" />
                Generate Plan
              </button>
              <button
                onClick={() => convertMutation.mutate()}
                disabled={!config || convertMutation.isPending}
                className="btn btn-secondary flex items-center justify-center gap-2"
              >
                <FileCode className="w-4 h-4" />
                Convert Only
              </button>
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Results</h2>

          {planMutation.isPending && <p>Generating plan...</p>}
          {convertMutation.isPending && <p>Converting configuration...</p>}

          {planMutation.isSuccess && planMutation.data?.data && (
            <div className="space-y-4">
              {/* Warnings */}
              {planMutation.data.data.warnings?.length > 0 && (
                <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-3">
                  <p className="font-semibold text-yellow-400 mb-2">Warnings:</p>
                  <ul className="list-disc list-inside text-sm text-yellow-400">
                    {planMutation.data.data.warnings.map((w: string, i: number) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Steps */}
              <div>
                <p className="font-semibold mb-2">Migration Steps:</p>
                <ol className="list-decimal list-inside text-sm space-y-1">
                  {planMutation.data.data.steps?.map((step: any, i: number) => (
                    <li key={i} className={step.manual ? 'text-yellow-400' : ''}>
                      {step.description}
                      {step.manual && ' (manual)'}
                    </li>
                  ))}
                </ol>
              </div>

              {/* Generated Config */}
              <div>
                <p className="font-semibold mb-2">Generated Configuration:</p>
                <pre className="bg-gray-900 p-3 rounded-lg overflow-auto max-h-48 text-xs font-mono">
                  {planMutation.data.data.target_config}
                </pre>
              </div>
            </div>
          )}

          {convertMutation.isSuccess && convertMutation.data?.data && (
            <div>
              <p className="font-semibold mb-2">Converted Configuration:</p>
              <pre className="bg-gray-900 p-3 rounded-lg overflow-auto max-h-96 text-xs font-mono">
                {convertMutation.data.data.converted_config}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Validation */}
      <div className="card mt-6">
        <h2 className="text-xl font-semibold mb-4">Migration Validation</h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <p className="text-gray-400">
              After migration, validate both resolvers return equivalent responses:
            </p>

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Test Domains (one per line, optional)
              </label>
              <textarea
                value={validationDomains}
                onChange={(e) => setValidationDomains(e.target.value)}
                placeholder="google.com&#10;cloudflare.com&#10;example.com"
                rows={5}
                className="input w-full font-mono text-sm"
              />
            </div>

            <button
              onClick={() => validateMutation.mutate()}
              disabled={validateMutation.isPending}
              className="btn btn-primary flex items-center justify-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              Run Validation
            </button>
          </div>

          <div>
            {validateMutation.isSuccess && validateMutation.data?.data && (
              <div className="space-y-4">
                <div
                  className={`p-4 rounded-lg ${
                    validateMutation.data.data.valid
                      ? 'bg-green-900/20 border border-green-800'
                      : 'bg-red-900/20 border border-red-800'
                  }`}
                >
                  <p
                    className={`text-lg font-semibold ${
                      validateMutation.data.data.valid ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {validateMutation.data.data.valid
                      ? '✓ Migration Validated'
                      : '✗ Validation Failed'}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">
                    {validateMutation.data.data.recommendation}
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="bg-gray-700/50 rounded-lg p-3">
                    <p className="text-xl font-bold">
                      {validateMutation.data.data.queries_tested}
                    </p>
                    <p className="text-xs text-gray-400">Tested</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-3">
                    <p className="text-xl font-bold text-green-400">
                      {validateMutation.data.data.matches}
                    </p>
                    <p className="text-xs text-gray-400">Matches</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-3">
                    <p className="text-xl font-bold text-red-400">
                      {validateMutation.data.data.mismatches}
                    </p>
                    <p className="text-xs text-gray-400">Mismatches</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
