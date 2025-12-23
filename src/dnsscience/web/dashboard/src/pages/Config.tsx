import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { CheckCircle, XCircle } from 'lucide-react'
import { getConfig, validateConfig } from '../api'
import { useStore } from '../store'

export default function Config() {
  const { resolver } = useStore()
  const [configText, setConfigText] = useState('')

  const { data: config, isLoading } = useQuery({
    queryKey: ['config', resolver],
    queryFn: () => getConfig(),
  })

  const validateMutation = useMutation({
    mutationFn: (config: string) => validateConfig(config, resolver),
  })

  const handleValidate = () => {
    if (configText) {
      validateMutation.mutate(configText)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Configuration</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Current Config */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Current Configuration</h2>

          {isLoading ? (
            <p>Loading...</p>
          ) : (
            <pre className="bg-gray-900 p-4 rounded-lg overflow-auto max-h-96 text-sm font-mono">
              {config?.data?.config || '# No configuration found'}
            </pre>
          )}
        </div>

        {/* Validate Config */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Validate Configuration</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Configuration to Validate
              </label>
              <textarea
                value={configText}
                onChange={(e) => setConfigText(e.target.value)}
                placeholder="Paste configuration here..."
                rows={12}
                className="input w-full font-mono text-sm"
              />
            </div>

            <button
              onClick={handleValidate}
              disabled={!configText || validateMutation.isPending}
              className="btn btn-primary w-full"
            >
              {validateMutation.isPending ? 'Validating...' : 'Validate'}
            </button>
          </div>

          {validateMutation.isSuccess && validateMutation.data?.data && (
            <div className="mt-4">
              {validateMutation.data.data.valid ? (
                <div className="p-3 bg-green-900/20 border border-green-800 rounded-lg text-green-400 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5" />
                  Configuration is valid
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="p-3 bg-red-900/20 border border-red-800 rounded-lg text-red-400 flex items-center gap-2">
                    <XCircle className="w-5 h-5" />
                    Configuration has errors
                  </div>

                  {validateMutation.data.data.errors?.length > 0 && (
                    <div className="bg-gray-700/50 p-3 rounded-lg">
                      <p className="font-semibold mb-2">Errors:</p>
                      <ul className="list-disc list-inside text-sm text-red-400">
                        {validateMutation.data.data.errors.map((err: any, i: number) => (
                          <li key={i}>
                            {err.line && `Line ${err.line}: `}
                            {err.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {validateMutation.data.data.warnings?.length > 0 && (
                <div className="mt-2 bg-yellow-900/20 p-3 rounded-lg border border-yellow-800">
                  <p className="font-semibold mb-2 text-yellow-400">Warnings:</p>
                  <ul className="list-disc list-inside text-sm text-yellow-400">
                    {validateMutation.data.data.warnings.map((warn: any, i: number) => (
                      <li key={i}>
                        {warn.line && `Line ${warn.line}: `}
                        {warn.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
