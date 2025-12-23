import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Service
export const getServiceStatus = () => api.get('/service/status')
export const startService = () => api.post('/service/start')
export const stopService = () => api.post('/service/stop')
export const restartService = () => api.post('/service/restart')
export const reloadService = () => api.post('/service/reload')

// Cache
export const getCacheStats = () => api.get('/cache/stats')
export const flushCache = () => api.delete('/cache')
export const purgeDomain = (domain: string) => api.delete(`/cache/${domain}`)

// Query
export const dnsQuery = (data: { name: string; record_type: string; dnssec?: boolean }) =>
  api.post('/query', data)
export const bulkQuery = (queries: Array<{ name: string; record_type: string }>) =>
  api.post('/query/bulk', { queries })
export const benchmarkQuery = (data: { name: string; count: number; concurrency: number }) =>
  api.post('/query/bench', data)

// Config
export const getConfig = () => api.get('/config')
export const validateConfig = (config: string, resolver: string) =>
  api.post('/config/validate', { config, resolver })
export const applyConfig = (config: string) => api.post('/config/apply', { config, reload: true })

// Compare
export const compareSingle = (domain: string, record_type: string) =>
  api.post('/compare', { domain, record_type })
export const compareBulk = (domains: string[], record_type: string) =>
  api.post('/compare/bulk', { domains, record_type })
export const startShadowMode = (config: object) => api.post('/compare/shadow/start', config)
export const stopShadowMode = () => api.post('/compare/shadow/stop')
export const getShadowReport = () => api.get('/compare/shadow/report')

// Migrate
export const createMigrationPlan = (source: string, target: string, config: string) =>
  api.post('/migrate/plan', { source, target, config })
export const convertConfig = (source: string, target: string, config: string) =>
  api.post('/migrate/convert', { source, target, config })
export const validateMigration = (domains?: string[]) =>
  api.post('/migrate/validate', { domains })

// Health
export const getHealth = () => api.get('/health')
export const getMetrics = () => api.get('/health/metrics')

export default api
