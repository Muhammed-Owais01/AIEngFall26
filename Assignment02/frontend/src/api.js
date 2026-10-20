export const getStatus = () => fetch('/api/status').then((r) => r.json())
export const runBenchmark = () => fetch('/api/run', { method: 'POST' })
