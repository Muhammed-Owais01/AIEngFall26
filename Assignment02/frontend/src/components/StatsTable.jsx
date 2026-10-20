const f = (x, d = 0) => (x == null ? '–' : x.toFixed(d))

export default function StatsTable({ slots, runs }) {
  const done = slots.filter((s) => runs[s.id]?.solved !== undefined)
  const wins = done.filter((s) => runs[s.id].solved).length
  return (
    <div className="card">
      <table>
        <thead><tr>
          {['Model', 'Result', 'Moves', 'Optimal gap', 'Avg live latency (ms)', 'Avg cached (ms)', 'Total time (s)',
            'API calls', 'Cache hits', 'Invalid', 'Cost ($)'].map((h) => <th key={h}>{h}</th>)}
        </tr></thead>
        <tbody>
          {done.map((s) => {
            const r = runs[s.id]
            return (
              <tr key={s.id}>
                <td>{s.label}</td><td>{r.solved ? 'solved' : 'unsolved'}</td><td>{r.move_count}</td>
                <td>{r.gap ?? '–'}</td><td>{f(r.avg_live_ms)}</td><td>{f(r.avg_cached_ms, 2)}</td>
                <td>{f(r.elapsed_s, 1)}</td><td>{r.api_calls}</td><td>{r.cache_hits}</td><td>{r.invalid}</td>
                <td>{f(r.cost, 4)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {done.length > 0 && (
        <small>Success rate: {wins}/{done.length} ({Math.round((100 * wins) / done.length)}%) · one puzzle, so each model is 0% or 100%</small>
      )}
    </div>
  )
}
