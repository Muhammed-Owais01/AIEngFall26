import Cube from './Cube'

export default function ModelCard({ slot, run = {}, maxTurns }) {
  const status = run.status || 'idle'
  const label = status === 'running' ? 'running…' : status === 'idle' ? 'idle'
    : status.toUpperCase() + (status === 'unsolved' ? ` (${run.reason})` : '')
  return (
    <div className="card">
      <b>{slot.label}</b> <small>{slot.provider}:{slot.model}</small><br />
      <span className={`badge ${status}`}>{label}</span>
      {run.state && <Cube state={run.state} />}
      <div>Current move: <b>{run.current || '–'}</b> · moves {(run.moves || []).length}/{maxTurns} · invalid {run.invalid || 0}</div>
      <div className="hist">{(run.moves || []).join(' ')}</div>
    </div>
  )
}
