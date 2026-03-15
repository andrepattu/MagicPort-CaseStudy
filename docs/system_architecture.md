# System architecture (Mermaid)

**Rationale:** The flow keeps raw data separate from the canonical vessel store so we can replay ingestion and reprocess after rule changes. Identity & Quality sits between raw and canonical so we never write invalid or unresolved identities into the master tables. Search (and any AI layer) talks only to the canonical store so results are consistent.

**Trade-offs:** Adding a dedicated Identity & Quality step increases latency and complexity compared to writing directly from ingestion; we accept that for data quality. Cache (in the conversational flow) is optional for the minimal case study; in production it reduces DB load and latency for repeated queries.

## High-level data and search flow

```mermaid
flowchart LR
    A[AIS / Registry] --> B[Ingestion]
    B --> C[Raw / Staging]
    C --> D[Identity & Quality]
    D --> E[Canonical Vessel Store]
    E --> F[Search API]
    F --> G[User / AI Client]
    G --> F
```

## Conversational AI and cache flow

```mermaid
flowchart TD
    U[User message] --> S[Session store]
    S --> NLU[NLU: intent + slots]
    NLU --> Q[Query builder]
    Q --> CK{Cache key}
    CK -->|hit| R[Return cached]
    CK -->|miss| DB[(Vessel DB)]
    DB --> Cache[Update cache]
    Cache --> Session[Update session]
    R --> Session
    Session --> NLG[NLG: format reply]
    NLG --> Out[Reply to user]
```

## Identity resolution pipeline

```mermaid
flowchart TD
    I[Input records] --> V[Validate IMO]
    V -->|invalid| F1[flag invalid_imo]
    V -->|valid| R[Resolve vessel_id]
    R --> M[MMSI → vessel_id + time]
    M --> C[Conflict check]
    C -->|same MMSI, different IMO| F2[flag conflict]
    C -->|ok| Store[Canonical store + history]
```
