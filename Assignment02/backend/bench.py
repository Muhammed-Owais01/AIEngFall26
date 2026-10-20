"""Run one model on one puzzle; shared by the API and the offline tests."""
import os
import time

import cube
import llm

DELAY = float(os.getenv("MOVE_DELAY_S", 1.0))  # pause after each move so the UI is watchable; excluded from timings
MAX_TURNS = 20  # a 3x3 is always solvable in <=20 moves (HTM)


def run_model(slot, start, optimal, progress):
    """progress: dict mutated in place so the UI can poll a live view."""
    progress.update(status="running", state=start, moves=[], current=None, invalid=0, api_calls=0, cache_hits=0,
                    cost=0.0, live_ms=[], cached_ms=[], elapsed_s=0.0)
    state, t0, reason, streak = start, time.perf_counter(), "move_limit", 0
    for _ in range(MAX_TURNS):
        if cube.is_solved(state):
            break
        try:
            r = llm.decide(slot, state, progress["moves"])
        except llm.BudgetExceeded as e:
            reason = f"call_cap: {e}"
            break
        except llm.ProviderError as e:
            reason = f"error: {e}"
            break
        progress["cost"] += r["cost"]
        if r["cached"]:
            progress["cache_hits"] += 1
            progress["cached_ms"].append(r["latency_ms"])
        else:
            progress["api_calls"] += 1
            progress["live_ms"].append(r["latency_ms"])
        if r["move"] is None:  # malformed: logged + counted, never converted into an action; still uses a turn
            progress["invalid"] += 1
            progress["current"] = "INVALID"
            streak += 1
            if streak >= 2:  # same prompt would repeat the same failure and burn calls
                reason = "invalid_output"
                break
            continue
        streak = 0
        state = cube.apply_move(state, r["move"])
        progress.update(state=state, current=r["move"])
        progress["moves"].append(r["move"])
        time.sleep(DELAY)
    solved = cube.is_solved(state)
    n = len(progress["moves"])
    avg = lambda a: sum(a) / len(a) if a else None
    progress.update(
        status="solved" if solved else "unsolved", reason="solved" if solved else reason, solved=solved, move_count=n,
        optimal=optimal, gap=n - optimal if solved else None, avg_live_ms=avg(progress["live_ms"]),
        avg_cached_ms=avg(progress["cached_ms"]), elapsed_s=time.perf_counter() - t0 - DELAY * n)
    return progress
