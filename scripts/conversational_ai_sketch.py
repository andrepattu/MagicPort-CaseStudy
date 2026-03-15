"""
Sketch: Caching and session management for conversational vessel search.
- In-memory cache for vessel search results (simulate Redis).
- Session store for conversation context (last filters, last result).
- Conversational layer queries the vessel data by calling the search function
  directly (e.g. vessel_search_from_dataframe); this is the "small illustrative
  code" path that satisfies the case study (implement caching and session).
No LLM or network calls; illustrates the flow and data structures.
"""
import hashlib
import json
import time

# In-memory cache (replace with Redis in production)
_cache = {}
_cache_ttl = {}
DEFAULT_TTL_SEC = 300  # 5 min


def cache_key(prefix: str, params: dict) -> str:
    """Stable key for caching query results."""
    canonical = json.dumps(params, sort_keys=True)
    return f"{prefix}:{hashlib.sha256(canonical.encode()).hexdigest()}"


def cache_get(key: str):
    """Return cached value if present and not expired."""
    if key not in _cache:
        return None
    if key in _cache_ttl and time.time() > _cache_ttl[key]:
        del _cache[key]
        del _cache_ttl[key]
        return None
    return _cache[key]


def cache_set(key: str, value, ttl_sec: int = DEFAULT_TTL_SEC):
    """Store value with TTL."""
    _cache[key] = value
    _cache_ttl[key] = time.time() + ttl_sec


# Session store (replace with Redis/DB in production)
_sessions = {}
SESSION_MAX_TURNS = 50
SESSION_IDLE_SEC = 1800  # 30 min


def get_or_create_session(session_id: str) -> dict:
    """Get session dict; create if missing. Reset if too old."""
    now = time.time()
    if session_id not in _sessions:
        _sessions[session_id] = {
            "created_at": now,
            "updated_at": now,
            "turn_count": 0,
            "current_filters": {},
            "last_result": None,
            "last_intent": None,
            "message_history": [],
        }
        return _sessions[session_id]
    s = _sessions[session_id]
    if now - s["updated_at"] > SESSION_IDLE_SEC or s["turn_count"] >= SESSION_MAX_TURNS:
        _sessions[session_id] = {
            "created_at": now,
            "updated_at": now,
            "turn_count": 0,
            "current_filters": {},
            "last_result": None,
            "last_intent": None,
            "message_history": [],
        }
        return _sessions[session_id]
    return s


def save_session(session_id: str, session: dict):
    """Persist session state."""
    session["updated_at"] = time.time()
    session["turn_count"] = session.get("turn_count", 0) + 1
    _sessions[session_id] = session


def merge_filters(current: dict, new_slots: dict) -> dict:
    """Merge new filter slots into current (new overrides)."""
    out = dict(current)
    for k, v in new_slots.items():
        if v is not None and v != "":
            out[k] = v
    return out


def vessel_search_from_dataframe(df, filters: dict, limit: int = 20):
    """
    Run a simple filter search on a DataFrame (stand-in for DB).
    filters: e.g. {"vessel_type": "Chemical Tanker", "flag": "PA", "builtYear_min": 2015}
    """
    subset = df
    if "vessel_type" in filters:
        subset = subset[subset["vessel_type"] == filters["vessel_type"]]
    if "flag" in filters:
        subset = subset[subset["flag"] == filters["flag"]]
    if "builtYear_min" in filters:
        subset = subset[subset["builtYear"].fillna(0).astype(int) >= filters["builtYear_min"]]
    if "name_contains" in filters:
        subset = subset[
            subset["name"].astype(str).str.contains(filters["name_contains"], case=False, na=False)
        ]
    return subset.head(limit).to_dict("records")


def handle_search_turn(session_id: str, slots: dict, df, limit: int = 20) -> dict:
    """
    One turn: merge slots into session filters, check cache, run search, update session.
    Conversational layer queries vessel data by calling vessel_search_from_dataframe
    (or in production, a DB/API); caching and session are the implemented behaviour.
    Returns {"result": [...], "filters": {...}, "from_cache": bool}.
    """
    session = get_or_create_session(session_id)
    filters = merge_filters(session.get("current_filters", {}), slots)
    key = cache_key("vessel_search", {**filters, "limit": limit})

    cached = cache_get(key)
    if cached is not None:
        session["current_filters"] = filters
        session["last_result"] = cached
        session["last_intent"] = "search_vessels"
        save_session(session_id, session)
        return {"result": cached, "filters": filters, "from_cache": True}

    result = vessel_search_from_dataframe(df, filters, limit=limit)
    cache_set(key, result)
    session["current_filters"] = filters
    session["last_result"] = result
    session["last_intent"] = "search_vessels"
    save_session(session_id, session)
    return {"result": result, "filters": filters, "from_cache": False}


if __name__ == "__main__":
    import os
    import sys
    import pandas as pd
    REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, REPO_ROOT)
    df = pd.read_csv(os.path.join(REPO_ROOT, "case_study_dataset_202509152039.csv"))
    df.columns = [c.strip() for c in df.columns]

    sid = "demo-session-1"
    r1 = handle_search_turn(sid, {"vessel_type": "Chemical Tanker", "flag": "PA"}, df, limit=5)
    print("Turn 1:", len(r1["result"]), "vessels", "from_cache:", r1["from_cache"])
    r2 = handle_search_turn(sid, {"vessel_type": "Chemical Tanker", "flag": "PA"}, df, limit=5)
    print("Turn 2:", len(r2["result"]), "vessels", "from_cache:", r2["from_cache"])
    r3 = handle_search_turn(sid, {"builtYear_min": 2010}, df, limit=5)
    print("Turn 3 (refined):", len(r3["result"]), "vessels", "from_cache:", r3["from_cache"])
    print("Session filters after turn 3:", r3["filters"])
    print("Done.")
