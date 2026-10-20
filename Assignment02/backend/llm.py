"""Model slots, providers, persistent cache + call counters (budget enforced here, before any request)."""
import hashlib
import json
import logging
import os
import re
import threading
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import cube

DATA = Path(os.getenv("DATA_DIR", "data"))
DATA.mkdir(exist_ok=True)
CACHE_FILE, COUNTER_FILE = DATA / "cache.json", DATA / "counters.json"

OPENROUTER_CAP = int(os.getenv("OPENROUTER_CAP", 5))   # Claude: max actual requests, ever
TOTAL_CAP = int(os.getenv("TOTAL_CAP", 65))            # overall: max actual requests, ever
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
TIMEOUT = 120  # same for every model; no retries (a retry is another billed/counted call)

# Three slots, identical prompt. Provider/model per slot is env-configurable (ollama | openrouter | mock | mock_opt).
SLOTS = [
    dict(id="clef", label="Clef", category="System-1 decision",
         provider=os.getenv("CLEF_PROVIDER", "ollama_decision"), model=os.getenv("CLEF_MODEL", "clef")),
    dict(id="qwen", label="Qwen", category="System-1 decision",
         provider=os.getenv("QWEN_PROVIDER", "ollama"), model=os.getenv("QWEN_MODEL", "qwen3")),
    dict(id="frontier", label="Frontier LLM (Claude Opus)", category="Frontier LLM",
         provider=os.getenv("FRONTIER_PROVIDER", "ollama"), model=os.getenv("FRONTIER_MODEL", "gemma3")),
]
SLOT = {s["id"]: s for s in SLOTS}

log = logging.getLogger("bench")
LOCK = threading.Lock()


class BudgetExceeded(Exception):
    pass


class ProviderError(Exception):
    pass


def _load(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def counters():
    c = _load(COUNTER_FILE)
    return {"by_model": c.get("by_model", {}), "openrouter": c.get("openrouter", 0), "total": c.get("total", 0)}


def build_prompt(state, recent):
    system = (
        "You solve a 3x3 Rubik's cube one move at a time. The cube is 54 facelets, faces in order "
        "U R F D L B, 9 stickers each, row-major as seen looking at that face. Each letter is the face "
        "that sticker belongs to; solved = every face a single letter. A move X turns face X clockwise "
        "90 degrees, X' counterclockwise, X2 by 180. Reply with exactly one JSON object: {\"move\": \"<move>\"}.")
    user = json.dumps({"cube_facelets": state, "recent_moves": recent[-6:], "allowed_moves": cube.MOVES,
                       "task": "Choose the single next move most likely to progress toward the solved cube."})
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    m = re.search(r"\{[^{}]*\}", text)
    try:
        mv = json.loads(m.group(0)).get("move") if m else None
    except json.JSONDecodeError:
        mv = None
    return mv if mv in cube.MOVES else None


def _ollama(slot, msgs, state):
    r = requests.post(f"{OLLAMA_HOST}/api/chat", timeout=TIMEOUT, json={
        "model": slot["model"], "messages": msgs, "stream": False, "think": False, "options": {"temperature": 0, "seed": 0},
        "format": {"type": "object", "properties": {"move": {"type": "string", "enum": cube.MOVES}},
                   "required": ["move"]}})
    r.raise_for_status()
    j = r.json()
    return j["message"]["content"], {"tokens": j.get("prompt_eval_count", 0) + j.get("eval_count", 0), "cost": 0.0}


def _ollama_decision(slot, msgs, state):  # System-1 "decisions" endpoint: typed choice question, no chat
    st = json.loads(msgs[1]["content"])
    desc = {m: f"Turn the {m[0]} face " + {"": "clockwise 90 degrees", "'": "counterclockwise 90 degrees",
                                          "2": "180 degrees"}[m[1:]] for m in cube.MOVES}
    r = requests.post(f"{OLLAMA_HOST}/v1/systemone", timeout=TIMEOUT, json={
        "model": slot["model"], "state": {"cube_facelets": st["cube_facelets"], "recent_moves": st["recent_moves"]},
        "questions": {"next_move": {"type": "choice", "instructions": st["task"], "criteria": desc}}})
    r.raise_for_status()
    j, a = r.json(), r.json()["answers"]["next_move"]
    u = j.get("usage", {})
    return json.dumps({"move": a["choice"]}), {"tokens": u.get("input_tokens", 0) + u.get("output_tokens", 0),
                                               "cost": 0.0, "confidence": a.get("confidence")}


def _openrouter(slot, msgs, state):
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise ProviderError("OPENROUTER_API_KEY not set")
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", timeout=TIMEOUT,
                      headers={"Authorization": f"Bearer {key}"}, json={
        "model": slot["model"], "messages": msgs, "temperature": 0, "max_tokens": 1000, "reasoning": {"effort": "low"}, "usage": {"include": True},
        "response_format": {"type": "json_schema", "json_schema": {"name": "move", "strict": True, "schema": {
            "type": "object", "properties": {"move": {"type": "string", "enum": cube.MOVES}},
            "required": ["move"], "additionalProperties": False}}}})
    r.raise_for_status()
    j = r.json()
    u = j.get("usage", {})
    ch = j["choices"][0]
    # keep the whole message when content is empty so an invalid reply can be diagnosed from the cache/log
    return ch["message"]["content"] or json.dumps({"empty_content": ch["message"], "finish": ch.get("finish_reason")}), {"tokens": u.get("total_tokens", 0), "cost": u.get("cost", 0.0)}


def _mock(slot, msgs, state):  # offline simulation: pseudo-random move, sometimes malformed
    h = int(hashlib.sha256(state.encode()).hexdigest(), 16)
    time.sleep(0.02)
    return ("garbage" if h % 7 == 0 else json.dumps({"move": cube.MOVES[h % 18]})), {"tokens": 0, "cost": 0.0}


def _mock_opt(slot, msgs, state):  # offline simulation: perfect player
    time.sleep(0.02)
    return json.dumps({"move": cube.optimal_solution(state)[0]}), {"tokens": 0, "cost": 0.0}


PROVIDERS = {"ollama": _ollama, "ollama_decision": _ollama_decision, "openrouter": _openrouter, "mock": _mock, "mock_opt": _mock_opt}


def decide(slot, state, recent):
    """One decision. Order: cache -> budget check -> log -> count -> request -> cache."""
    msgs = build_prompt(state, recent)
    prov, offline = slot["provider"], slot["provider"].startswith("mock")
    key = hashlib.sha256(json.dumps([prov, slot["model"], msgs]).encode()).hexdigest()
    t = time.perf_counter()
    if not offline:
        with LOCK:
            hit = _load(CACHE_FILE).get(key)
        if hit:
            log.info("[%s] CACHE HIT (%.2f ms)", slot["id"], (time.perf_counter() - t) * 1000)
            return {**hit, "cached": True, "latency_ms": (time.perf_counter() - t) * 1000,
                    "orig_latency_ms": hit["latency_ms"]}
    ck = f"{prov}:{slot['model']}"
    if not offline:
        with LOCK:
            c = counters()
            if c["total"] >= TOTAL_CAP:
                raise BudgetExceeded(f"total cap {TOTAL_CAP} reached")
            if prov == "openrouter" and c["openrouter"] >= OPENROUTER_CAP:
                raise BudgetExceeded(f"openrouter cap {OPENROUTER_CAP} reached")
            log.info("[%s] LIVE REQUEST %s | before: total=%d openrouter=%d model_calls=%d", slot["id"], ck,
                     c["total"], c["openrouter"], c["by_model"].get(ck, 0))
            c["total"] += 1
            c["openrouter"] += prov == "openrouter"
            c["by_model"][ck] = c["by_model"].get(ck, 0) + 1
            _save(COUNTER_FILE, c)  # persisted before the request, so a crash can't leak calls
    t = time.perf_counter()
    try:
        raw, meta = PROVIDERS[prov](slot, msgs, state)
    except Exception as e:  # network/HTTP error: counted, not cached, not retried
        raise ProviderError(str(e)) from e
    entry = {"raw": raw, "move": _parse(raw), "latency_ms": (time.perf_counter() - t) * 1000, **meta}
    if not offline and entry["move"]:  # invalid replies are never cached: a retry must be a real new call
        with LOCK:
            cache = _load(CACHE_FILE)
            cache[key] = entry
            _save(CACHE_FILE, cache)
    log.info("[%s] live latency %.0f ms -> %s", slot["id"], entry["latency_ms"], entry["move"] or f"INVALID {raw!r}")
    return {**entry, "cached": False}
