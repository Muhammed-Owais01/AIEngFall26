"""Deterministic 3x3 cube engine on a 54-char facelet string (URFDLB, 9 per face, row-major).

Stickers are modelled as (position, normal) in 3D, so every move is a plain rotation and
there are no hand-typed permutation tables to get wrong.
"""
import random
from collections import deque

FACES = "URFDLB"
NORMAL = {"U": (0, 1, 0), "R": (1, 0, 0), "F": (0, 0, 1), "D": (0, -1, 0), "L": (-1, 0, 0), "B": (0, 0, -1)}
MOVES = [f + s for f in FACES for s in ("", "'", "2")]  # 18 moves, half-turn metric
SOLVED = "".join(f * 9 for f in FACES)


def _pos(f, r, c):  # x right, y up, z front; r/c = row/col as seen looking at the face
    return {"U": (-1 + c, 1, -1 + r), "R": (1, 1 - r, 1 - c), "F": (-1 + c, 1 - r, 1),
            "D": (-1 + c, -1, 1 - r), "L": (-1, 1 - r, -1 + c), "B": (1 - c, 1 - r, -1)}[f]


_STICKERS = [(_pos(f, r, c), NORMAL[f]) for f in FACES for r in range(3) for c in range(3)]
_INDEX = {s: i for i, s in enumerate(_STICKERS)}


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _cw(n, v):  # rotate v by -90deg about n (= clockwise seen from outside face n)
    d = sum(x * y for x, y in zip(n, v))
    return tuple(-c + x * d for c, x in zip(_cross(n, v), n))


def _perm(face):
    n, p = NORMAL[face], list(range(54))
    for i, (pos, nor) in enumerate(_STICKERS):
        if sum(a * b for a, b in zip(pos, n)) == 1:
            p[_INDEX[(_cw(n, pos), _cw(n, nor))]] = i  # new[j] = old[i]
    return p


_PERM = {f: _perm(f) for f in FACES}


def apply_move(state, move):
    p = _PERM[move[0]]
    for _ in range({"": 1, "'": 3, "2": 2}[move[1:]]):
        state = "".join(state[i] for i in p)
    return state


def apply_moves(state, moves):
    for m in moves:
        state = apply_move(state, m)
    return state


def is_solved(state):
    return all(len(set(state[i * 9:i * 9 + 9])) == 1 for i in range(6))


def inverse(move):
    return move if move.endswith("2") else (move[0] if move.endswith("'") else move + "'")


def _bfs_table(depth):
    """state -> (distance, move that brings it one step closer to solved). Exact, from solved."""
    table, q = {SOLVED: (0, None)}, deque([SOLVED])
    while q:
        s = q.popleft()
        d = table[s][0]
        if d == depth:
            continue
        for m in MOVES:
            t = apply_move(s, m)
            if t not in table:
                table[t] = (d + 1, inverse(m))
                q.append(t)
    return table


_TABLE = _bfs_table(3)  # ~ 6k states; covers every scramble of <=3 moves


def optimal_distance(state):
    """Exact shortest solution length for states within 3 moves of solved, else None."""
    e = _TABLE.get(state)
    return e[0] if e else None


def optimal_solution(state):
    sol = []
    while state != SOLVED:
        m = _TABLE[state][1]
        sol.append(m)
        state = apply_move(state, m)
    return sol


def scramble(seed, n=3):
    """Seeded scramble that is exactly n (<=3) moves from solved (verified by BFS, not assumed)."""
    rng = random.Random(seed)
    while True:
        seq = []
        while len(seq) < n:
            m = rng.choice(MOVES)
            if not seq or seq[-1][0] != m[0]:
                seq.append(m)
        s = apply_moves(SOLVED, seq)
        if optimal_distance(s) == n:
            return s, seq
