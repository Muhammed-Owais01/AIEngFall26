import logging
import os
import threading

from fastapi import FastAPI, HTTPException

import bench
import cube
import llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(llm.DATA / "run.log")])
app = FastAPI()

PUZZLE = {}
RUNS = {}  # slot id -> live/final progress dict for the current puzzle
RESULTS_FILE = llm.DATA / "results.json"
BUSY = threading.Event()


def set_puzzle(seed):
    st, seq = cube.scramble(seed)
    PUZZLE.update(seed=seed, state=st, scramble=seq, optimal=cube.optimal_distance(st),
                  optimal_solution=cube.optimal_solution(st))
    RUNS.clear()
    saved = llm._load(RESULTS_FILE).get(str(seed), {})
    RUNS.update(saved)  # restore earlier results for this puzzle after a restart


set_puzzle(int(os.getenv("PUZZLE_SEED", 42)))


def worker(ids):
    try:
        for i in ids:
            slot = llm.SLOT[i]
            RUNS[i] = {"status": "queued"}
            bench.run_model(slot, PUZZLE["state"], PUZZLE["optimal"], RUNS[i])
            RUNS[i].update(label=slot["label"], category=slot["category"], provider=slot["provider"], model=slot["model"])
            allr = llm._load(RESULTS_FILE)
            allr.setdefault(str(PUZZLE["seed"]), {})[i] = RUNS[i]
            llm._save(RESULTS_FILE, allr)
    finally:
        BUSY.clear()


@app.get("/api/status")
def status():
    return {"puzzle": PUZZLE, "runs": RUNS, "busy": BUSY.is_set(), "counters": llm.counters(),
            "caps": {"openrouter": llm.OPENROUTER_CAP, "total": llm.TOTAL_CAP, "max_turns": bench.MAX_TURNS},
            "slots": llm.SLOTS, "student": os.getenv("STUDENT_NAME", "Your Name"), "roll": os.getenv("STUDENT_ROLL", "Roll No")}


@app.post("/api/puzzle/{seed}")
def new_puzzle(seed: int):
    if BUSY.is_set():
        raise HTTPException(409, "benchmark running")
    set_puzzle(seed)
    return PUZZLE


@app.post("/api/run")
def run(slots: str = ""):
    """slots: comma-separated slot ids, default all four (sequential, same puzzle)."""
    ids = [s for s in slots.split(",") if s] or [s["id"] for s in llm.SLOTS]
    if any(i not in llm.SLOT for i in ids):
        raise HTTPException(400, "unknown slot")
    if BUSY.is_set():
        raise HTTPException(409, "benchmark already running")
    BUSY.set()
    RUNS.clear()
    threading.Thread(target=worker, args=(ids,), daemon=True).start()
    return {"started": ids}

