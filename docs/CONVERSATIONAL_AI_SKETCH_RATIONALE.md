# In-depth rationale and goal of `scripts/conversational_ai_sketch.py`

## Goal

The script is a **design-level implementation** of the **conversational vessel search** layer described in the case study. Its goal is to show how **caching** and **session management** work in practice so that:

1. Repeated or refined vessel queries are cheap and fast (cache).
2. Multi-turn conversations keep context (session) so follow-ups like “narrow to built after 2010” apply on top of the previous filters.

It is **not** a full production service. It has no LLM, no real NLU/NLG, and no database—only in-memory structures. The conversational layer queries vessel data by **calling the search function directly** (e.g. `vessel_search_from_dataframe`); the case study asks for “small illustrative code” and does not require a REST API. The goal is to make the **data flow and responsibilities** of the conversational layer clear and runnable.

---

## Rationale

### 1. Why this script exists

The case study asks to:

- “Implement caching and session management to optimize repeated vessel queries and maintain conversational context.”
- “Architect the conversational AI so the LLM can query structured vessel databases particularly when the query is asking various filters.”

A design document alone is not enough to show how caching keys are built or how sessions store “current filters” and “last result.” This script **implements those mechanisms** in small, readable form so reviewers can run it and see cache hits and session merge behavior. The conversational layer talks to the data side by **calling the search function directly** (e.g. on a DataFrame as stand-in for a DB); that satisfies the case study’s “architect so the LLM can query structured vessel databases” without implementing a full API.

### 2. Caching: what and why

- **What:** A key–value cache keyed by a **normalized representation of the search request** (filters + limit). Same request → same key → return cached list of vessels; no need to hit the database or the API again.
- **Why:** In a real product, users and the LLM often repeat the same or similar queries (e.g. “Container ships under Singapore” twice, or “same but built after 2020” then “same but built after 2015”). Caching reduces load on the vessel DB and latency for the user. The script uses in-memory dicts with TTL to **stand in for Redis**; the interface (cache_key, cache_get, cache_set) is the same one you’d use with Redis in production.
- **Scope:** Only **query results** are cached (the list of vessels returned for a given filter set). Session state (current filters, last result) is separate and lives in the session store.

### 3. Session management: what and why

- **What:** A **per-session store** that holds:
  - `current_filters`: the accumulated filter state (e.g. vessel_type=Container, flag=SG, builtYear_min=2020).
  - `last_result`: the last list of vessels returned (so the next turn can say “I’ve narrowed the previous 12 to 5” or “here are the next 5”).
  - `last_intent`, `message_history`, and timestamps for optional NLU and session lifecycle.
- **Why:** Conversational search is multi-turn. The user might say “Chemical tankers under Panama,” then “only built after 2015,” then “what about Singapore?” Without session state, the second and third utterances have no prior context. By **merging new slots into current_filters**, the script models “refine previous search” and “change one dimension”: the backend always receives a full filter set (previous + new), so the vessel API/DB is queried with one coherent request. Session expiry (idle timeout, max turns) keeps state bounded and avoids leaking memory or stale context.

### 4. How it fits in the pipeline

The script is self-contained: it loads the CSV into a dataframe and runs pandas filters via `vessel_search_from_dataframe`. That shows the **logic** of cache key, session merge, and “one turn” (handle_search_turn) without any network. The **pipeline** is: **User → (future: NLU) → conversational layer (cache + session + query builder) → search function → vessel data (DataFrame or, in production, DB).** The case study asks for “small illustrative code” and “implement caching and session management”; the conversational layer querying a structured vessel source by **calling the search function directly** satisfies “architect so the LLM can query structured vessel databases” without requiring a REST API.

### 5. What is intentionally omitted

- **LLM / NLU / NLG:** The case study asks for a design and illustrative code, not a full chatbot. So the script does **not** parse natural language or generate replies; it only consumes **slots** (e.g. `{"vessel_type": "Chemical Tanker", "flag": "PA"}`) and returns structured results. In a full system, an NLU step would turn “Show me chemical tankers under Panama” into those slots, and an NLG step would turn the result list into natural language.
- **Real Redis/DB:** In-memory dicts keep the script runnable with zero infrastructure and make the caching/session **contract** clear; swapping to Redis or a DB is a deployment detail.
- **Auth, rate limits, validation:** Out of scope for this sketch; they would live in the API or a gateway in production.

---

## Summary

| Aspect | Purpose |
|--------|--------|
| **Goal** | Demonstrate caching and session management for conversational vessel search in runnable code. |
| **Caching** | Same filter set → cache hit → no duplicate DB/API call; key = hash of normalized params; TTL for freshness. |
| **Session** | Persist current_filters and last_result so follow-up turns merge new slots and preserve context. |
| **Pipeline role** | Implements the “conversational layer” that calls the vessel search function directly (DataFrame as stand-in for DB); no API required by the case study. |
| **Omissions** | No LLM/NLU/NLG; in-memory store instead of Redis; no auth or rate limits. |

**Trade-offs (explicit):** In-memory cache and session avoid Redis so the script runs with zero infrastructure, at the cost of state lost on restart. Direct call to the search function (no REST API) keeps the submission as "small illustrative code" per the case study; production might add an API for scale and polyglot clients. Slot-based input (no NLU) demonstrates caching and session merge without LLM cost and variability.

The script is the **bridge** between “user conversation” (future: LLM) and “structured vessel data”: it turns multi-turn intent into a single, cacheable, session-aware request to the vessel search function and stores the result for the next turn.
