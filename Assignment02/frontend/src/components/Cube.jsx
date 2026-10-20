const COLORS = { U: '#f5f5f5', R: '#c1121f', F: '#2a9d4a', D: '#ffd60a', L: '#ff7b00', B: '#1d6fe0' }
// each face is a 3x3 grid; transforms put it on the cube (rows/cols match the backend's facelet order)
const FACE_T = {
  U: 'rotateX(90deg)', D: 'rotateX(-90deg)', F: '', B: 'rotateY(180deg)', R: 'rotateY(90deg)', L: 'rotateY(-90deg)',
}

export default function Cube({ state, size = 120 }) {
  const half = size / 2
  return (
    <div className="scene" style={{ width: size, height: size, margin: `${size * 0.35}px auto` }}>
      <div className="cube3d">
        {'URFDLB'.split('').map((f, fi) => (
          <div key={f} className="face" style={{ width: size, height: size, transform: `${FACE_T[f]} translateZ(${half}px)` }}>
            {[...state.slice(fi * 9, fi * 9 + 9)].map((c, i) => <i key={i} style={{ background: COLORS[c] }} />)}
          </div>
        ))}
      </div>
    </div>
  )
}
