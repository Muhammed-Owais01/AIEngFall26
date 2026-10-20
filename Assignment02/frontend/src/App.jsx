import { useEffect, useState } from 'react'
import { getStatus, runBenchmark } from './api'
import Cube from './components/Cube'
import ModelCard from './components/ModelCard'
import StatsTable from './components/StatsTable'

export default function App() {
  const [s, setS] = useState(null)
  useEffect(() => {
    const tick = () => getStatus().then(setS).catch(() => {})
    tick()
    const t = setInterval(tick, 700)
    return () => clearInterval(t)
  }, [])
  if (!s) return <main>Connecting to backend…</main>

  const { puzzle: p, counters: c, caps, runs, slots } = s
  return (
    <>
      <div className="banner">{s.student} — {s.roll}</div>
      <main>
        <h2>Rubik's Cube Race <small>exactly-3-move scramble · {caps.max_turns}-move limit</small></h2>
        <p>
          <button disabled={s.busy} onClick={() => runBenchmark()}>Run benchmark</button>{' '}
          Actual API calls: {c.total}/{caps.total} · OpenRouter: {c.openrouter}/{caps.openrouter}
        </p>
        <div className="card">
          <b>Start state</b> (seed {p.seed}, scramble {p.scramble.join(' ')}, exact optimal = {p.optimal} moves)
          <Cube state={p.state} size={150} />
        </div>
        <div className="grid">
          {slots.map((sl) => <ModelCard key={sl.id} slot={sl} run={runs[sl.id]} maxTurns={caps.max_turns} />)}
        </div>
        <h3>Benchmark</h3>
        <StatsTable slots={slots} runs={runs} />
      </main>
    </>
  )
}
