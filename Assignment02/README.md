# Rubik's Cube Race (Assignment 02)

**Muhammad Owais - 23K-0047**

## Demo screen recording

**[Watch the screen recording (demo/rubiks-cube-race-demo.mp4)](https://github.com/Muhammed-Owais01/AIEngFall26/blob/main/Assignment02/demo/rubiks-cube-race-demo.mp4)** - in-repo file: [`demo/rubiks-cube-race-demo.mp4`](demo/rubiks-cube-race-demo.mp4)

## Experiment results

**Setup.** One puzzle, seed 42: scramble `R U F2`, exact optimal solution `F2 U' R'` = **3 moves** (BFS-verified). Every model got the same start state, the same prompt, the same 18-move set, a 20-turn limit and no retries. Optimality gap = moves used - 3 (only defined when solved). Clef and Qwen ran locally on Ollama (live run, then cached); Claude Opus 5.5 ran through OpenRouter.

| Model | Category | Result | Moves | Optimal gap | Avg live latency / move | Total decision time | API calls | Cache hits | Invalid replies | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| clef-flash (`/v1/systemone` decision API) | System-1 decision | **Unsolved** (20-move limit) | 20 | n/a | 3,938 ms (3,617-4,634) | 78.8 s | 20 | 0 | 0 | $0 (local) |
| qwen3.5 (Ollama chat, think off) | Frontier-style LLM, local | **Unsolved** (20-move limit) | 20 | n/a | 2,892 ms (2,745-3,065) | 57.8 s | 20 | 0 | 0 | $0 (local) |
| claude-opus-5.5 (OpenRouter) | Frontier LLM | **Unsolved** (5-call cap reached) | 3 valid (`F' F F'`) | n/a | 9,259 ms over its 3 valid calls; 8,561 ms over all 5 (3,774-17,154) | 27.8 s for the 3 valid calls | 5 live | 0 | 2 (empty replies) | about $0.04 |

Notes on the table:
- Latencies are live Ollama/OpenRouter latencies taken from `backend/data/run.log`. Reruns served from the cache take about 1 ms per move and are reported separately in the dashboard (`Avg cached`), never mixed with live latency.
- Clef and Qwen: `api_calls`/latency are from their first live run; a later cached rerun shows 20 cache hits and 0 calls. Total decision time excludes the 1 s `MOVE_DELAY_S` display pause.
- Opus: the first 2 calls returned empty content (the 200-token limit was too small, fixed later), and they counted toward the 5-call cap. The 3 valid calls cost $0.0212, $0.0052 and $0.0028 = $0.0291; one invalid call was logged at $0.0065 and the other's cost was not recorded, so total is about $0.04. Opus was left 3 moves from solved, the same as the start.
- Final cube distance: Clef and Qwen finished farther than 3 moves from solved (their random-looking `U`/`R` turns scrambled the cube further); Opus's `F' F F'` cancels to a single `F'`.

**Success rate:** Clef 0/1 (0%), Qwen 0/1 (0%), Opus 0/1 (0%). Nobody solved the cube, so no optimality gaps exist.

**Budget used:** 5 of 5 OpenRouter calls and 54 counted calls overall (cap 65). The extra 9 calls beyond the runs above are local Ollama setup/debug calls (wrong model tag, endpoint errors, a CUDA load failure, uninstalled `deepseek-r1`/`gemma3` tests).

### Answers to the assignment questions

1. **Fastest decisions?** Qwen3.5 (2.9 s/move), then Clef-flash (3.9 s), then Opus (8.6-9.3 s). Both local models are faster than the remote frontier model, but both ran on local hardware, so this partly measures the machine and the network, not only the model. The decision model was not faster than the small chat LLM here.
2. **Highest solve rate?** A three-way tie at 0%. One puzzle, one attempt each, so this says little about the models in general.
3. **Shortest solutions / closeness to optimum?** None: no model solved the cube. The optimum is 3 moves and nobody got there.
4. **Did the fastest model also give the best quality?** No. Qwen was fastest but neither it nor anyone else solved the cube. Opus was the slowest and came closest in behaviour (it never made the cube worse), but did not solve it within its 3 valid calls.
5. **What would I use?** On this evidence none of these models should be used alone: Clef and Qwen drift away from the solution, and Opus was slow and expensive for 3 non-solving moves. For a real cube-solving application I would use a hybrid: an exact solver (like the BFS here) for the moves, and a model only where language is needed. This is one puzzle and one run per model, with Opus given only 3 valid moves by the budget; it is weak evidence, not a general conclusion.

### Deviations from the assignment
- Jev, GPT-6 Luna and the OpenRouter Decisions API were not used; Clef-flash and Qwen3.5 on Ollama stand in. Clef uses Ollama's `/v1/systemone` decision endpoint (same typed-choice shape as the Decisions API).
- Only 3 models (DeepSeek removed), 1 puzzle (a 3-move scramble, not the 4-5 move primary benchmark) because of the call budget.
- OpenRouter's 5-call budget is a hard cap in the backend; 2 of the 5 were lost to the empty-reply issue.

## About

Three models (Clef, Qwen, Claude Opus) play the same cube (exactly 3 moves from solved, seeded) through one prompt/move contract.
Optimal distance is exact (BFS), gap = model moves - 3. Max 20 turns, then "unsolved".

## Layout
    backend/    FastAPI + cube engine + model adapters, cache, budget (data/ is created here)
    frontend/   React (Vite) UI, proxies /api to the backend

## Setup
    cd backend
    pip install -r requirements.txt
    cp .env.example .env      # set name/roll, Ollama model tags
    python test_sim.py        # offline checks, zero API calls
    uvicorn app:app           # API on :8000

    cd frontend
    npm install
    npm run dev               # open http://localhost:5173, click "Run benchmark"

## Budget safety
- Every request is looked up in `data/cache.json` first (key = provider+model+prompt); hits cost nothing and are timed separately from live latency.
- Counters persist in `data/counters.json` and are written *before* each request. Never reset on restart. Delete `data/` only deliberately.
- OpenRouter hard cap 5 (Claude), total cap 65; errors are not retried. Run stops "unsolved (call_cap)" when hit.
- Ollama is the default for all slots; set `FRONTIER_PROVIDER=openrouter` + `OPENROUTER_API_KEY` for the one Claude run.

Not implemented: OpenRouter Decisions API adapter (response schema unverified; Ollama stands in for the decision models).
