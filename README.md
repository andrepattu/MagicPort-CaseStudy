# MagicPort Case Study: Vessel Identification & AI Agent

Case study deliverables for the **Data and AI Engineer** role at [MagicPort](https://magicport.ai/), addressing vessel identity resolution, data quality, and an AI-powered vessel search design.

## Contents

| Item | Description |
|------|-------------|
| **docs/DESIGN_DOCUMENT.md** | High-level design: data quality, identity resolution, system architecture, conversational AI, tool choices (with rationale and trade-offs), evaluation |
| **scripts/** | Python modules: data exploration, IMO validation, vessel identity resolution, conflict detection, conversational AI sketch (cache + session) |
| **notebooks/** | Jupyter notebook for dataset exploration and illustrative code |
| **docs/** | System architecture (Mermaid), rationale for conversational_ai_sketch.py |

## Quick Start

```bash
# Create virtualenv (recommended)
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run data exploration and identity-resolution snippets
python scripts/explore_dataset.py
python scripts/vessel_identity.py

# Run conversational layer: caching and session (calls vessel search function directly)
python scripts/conversational_ai_sketch.py
```

## Dataset

- **File:** `case_study_dataset_202509152039.csv`
- **Rows:** 1,734 vessel records (static + AIS-style attributes)
- **Key identifiers:** IMO (permanent), MMSI (can change over time)

## Interpreting the script outputs

- **explore_dataset.py** — Summarises the CSV: row/column counts, column groups (static, AIS/position, voyage, meta), IMO validity (checksum: 1064 valid, 66 distinct invalid values, 252 with IMO=0), MMSI (9-digit count, duplicate MMSI rows), IMO→multiple MMSIs (209 IMOs; many are placeholders like 0/1000000; real vessels like 1006568 show flag/MMSI change over time), MMSI→multiple IMOs (conflicts), duplicate (IMO, MMSI) pairs, missing key fields (name, vessel_type, flag), and value counts for vessel_type and flag. Use this to understand data quality before identity resolution.
- **vessel_identity.py** — Flags invalid IMO (670 rows), IMO–MMSI conflicts (0 in this dataset), duplicate (imo, mmsi) rows (0); shows an example vessel (valid IMO with multiple MMSIs over time, e.g. LADY DUVERA) and the `same_vessel()` heuristic: (invalid IMO ⇒ False), (valid IMO, same vessel ⇒ True).
- **conversational_ai_sketch.py** — Demonstrates caching and session: Turn 1 runs a search (e.g. Chemical Tanker, PA) and returns 5 vessels (from_cache: False). Turn 2 with the same filters returns from cache (from_cache: True). Turn 3 refines with e.g. builtYear_min=2010; session merges filters so the effective query is vessel_type + flag + builtYear_min, and returns a new result (from_cache: False). Session filters after turn 3 show the accumulated state.

Reasoning and trade-offs for design choices (identity, validation, tool choices, etc.) are in **docs/DESIGN_DOCUMENT.md** and **docs/CONVERSATIONAL_AI_SKETCH_RATIONALE.md**.

## Key Questions Addressed (in design document)

1. When do two records refer to the same vessel?
2. How to detect and flag invalid or conflicting records?
3. How to track vessel changes over time (name, flag, MMSI)?
4. Is a "ground truth" vessel database realistic?
5. System design for search & retrieval?
6. Conversational AI for vessel search?
7. Preventing LLM hallucinations?
8. Evaluation methods for AI-powered vessel search?


Copyright [Year] [Your Name]. All rights reserved.

This repository is provided solely for review. No usage, modification, distribution, or reproduction of this code is allowed for any purpose without explicit written permission from the author.
