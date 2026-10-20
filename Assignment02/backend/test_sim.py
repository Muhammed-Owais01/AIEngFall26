"""Offline checks (no Ollama, no OpenRouter): python test_sim.py"""
import os
import tempfile

os.environ["MOVE_DELAY_S"] = "0"
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import bench
import cube
import llm

# --- engine sanity
S = cube.SOLVED
assert all(cube.apply_moves(S, [m] * 4) == S for m in ("U", "R", "F", "D", "L", "B"))
assert cube.apply_moves(S, ["R", "U", "R'", "U'"] * 6) == S
assert cube.apply_move(cube.apply_move(S, "U"), "U'") == S and cube.apply_move(S, "U2") == cube.apply_moves(S, ["U", "U"])
u = cube.apply_move(S, "U")  # U clockwise: F top row takes R's colour
assert u[18:21] == "RRR" and u[9:12] == "BBB"
for seed in range(30):
    st, seq = cube.scramble(seed)
    assert cube.optimal_distance(st) == 3 and len(cube.optimal_solution(st)) == 3
    assert cube.is_solved(cube.apply_moves(st, cube.optimal_solution(st)))

start, _ = cube.scramble(42)
slot = lambda p: dict(id="t", label="t", category="t", provider=p, model="m")

# --- perfect player: solves in 3, gap 0
r = bench.run_model(slot("mock_opt"), start, 3, {})
assert r["solved"] and r["move_count"] == 3 and r["gap"] == 0, r

# --- bad player: hits the 20-turn limit, unsolved, malformed outputs counted
r = bench.run_model(slot("mock"), start, 3, {})
assert not r["solved"] and r["move_count"] + r["invalid"] <= 20 and r["reason"] in ("move_limit", "invalid_output"), r

# --- cache + caps with a fake "remote" provider that plays optimally
calls = []
def fake(s, msgs, state):
    calls.append(1)
    return llm.PROVIDERS["mock_opt"](s, msgs, state)
llm.PROVIDERS["openrouter"] = fake
llm.PROVIDERS["ollama"] = fake
r1 = bench.run_model(slot("ollama"), start, 3, {})
assert r1["api_calls"] == 3 and r1["cache_hits"] == 0 and len(calls) == 3
r2 = bench.run_model(slot("ollama"), start, 3, {})  # identical rerun -> all cache, zero calls
assert r2["api_calls"] == 0 and r2["cache_hits"] == 3 and len(calls) == 3 and r2["solved"]
assert llm.counters()["total"] == 3

llm.OPENROUTER_CAP = 2  # claude-style cap: stops mid-run, marked unsolved, never exceeds the cap
r3 = bench.run_model(slot("openrouter"), start, 3, {})
assert not r3["solved"] and r3["api_calls"] == 2 and r3["reason"].startswith("call_cap"), r3
assert llm.counters()["openrouter"] == 2
r4 = bench.run_model(slot("openrouter"), start, 3, {})  # rerun: 2 cached, then cap hit, no new calls
assert r4["api_calls"] == 0 and r4["cache_hits"] == 2 and llm.counters()["openrouter"] == 2
print("all offline checks passed")
