# Rubik's Cube Race (Assignment 02)

**Muhammad Owais - 23K-0047**

## Demo screen recording

**[Watch the screen recording (demo/rubiks-cube-race-demo.mp4)](https://github.com/Muhammed-Owais01/AIEngFall26/blob/main/Assignment02/demo/rubiks-cube-race-demo.mp4)** - in-repo file: [`demo/rubiks-cube-race-demo.mp4`](demo/rubiks-cube-race-demo.mp4)

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
