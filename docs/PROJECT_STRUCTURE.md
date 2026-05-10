# Project structure

Layout for the Text2SQL backend and scripts. Keeps agents, services, and config organized as more agents are added (Table, Column, Few-Shot, Gen-SQL, SQL Validator).

## Root

```
Text2SQL project/
├── .env
├── docs/
│   ├── PROJECT_STRUCTURE.md      # this file
│   ├── CHAT_UI_AND_SESSIONS.md   # multi-chat UI, GET /sessions, client_id, localStorage
│   ├── MULTI_CHAT_SIDEBAR_PLAN.md # pointer: multi-chat feature status + link to CHAT_UI doc
│   ├── STAGE1_FINALIZED_PLAN.md
│   ├── TABLE_AGENT_5A_PLAN.md    # Table Agent implementation plan (5a)
│   ├── COLUMN_AGENT_5B_PLAN.md   # Column Agent implementation plan (5b)
│   ├── INSTALLATION_REQUIREMENTS.md
│   ├── SUPABASE_SETUP.md           # hosted Postgres: URI, password, schema, sessions
│   ├── RELATIONSHIPS_PIPELINE.md   # FK table_relationships pipeline (per-domain schema)
│   └── Text2SQL_PostgreSQL_Setup_Guide.md
├── requirements.txt
├── build_vector_store.py         # table/column metadata → FAISS + metadata_store
├── build_relationship_embeddings.py  # FK table_relationships → embeddings JSON (no FAISS)
├── build_few_shot_metadata_store.py  # system_schema.few_shot_examples → metadata_store JSON
├── build_business_rules_vector_store.py   # business rules → FAISS + business_rules_store
├── generate_data.py
├── faiss_indexes/                # FAISS indexes (schema + business_rules_*)
├── metadata_store/               # table/column metadata JSON (per schema)
├── business_rules_store/         # business-rules metadata JSON (per schema)
├── backend/                      # API and pipeline
├── scripts/                      # create_app_schema.sql, backfill_session_metadata.sql, run_*.py, domain FK DDL, migrations
└── frontend/                     # Chat UI: sidebar (multi-session), thread, composer; index.html, styles.css, app.js; served at / by FastAPI
```

## Backend

```
backend/
├── __init__.py
├── config.py                     # PROJECT_ROOT, get_engine(), DOMAIN_SCHEMAS, paths, RELATIONSHIP_METADATA_NAMES, USE_CASES
├── agents/                       # one module per agent
│   ├── __init__.py
│   ├── intent_agent.py           # Stage 1: rephrase + keywords + business_insights
│   ├── few_shot_agent.py         # LLM picks pattern ids (id + question + type); returns full rows for Gen-SQL
│   ├── table_agent.py            # Table selection: shortlist + LLM → selected_tables (schema.table); FK-aware
│   ├── column_agent.py           # Column selection: shortlist + LLM → selected_columns per table; FK-aware
│   ├── gen_sql_agent.py          # SQL synthesis from context + few-shot; optional relationship_text lines
│   └── ...
├── services/                     # shared services used by agents
│   ├── __init__.py
│   ├── business_rules_retrieval.py   # FAISS retrieval → list of insight strings
│   ├── llm_client.py                 # OpenAI / Gemini chat_completion
│   ├── table_metadata_retrieval.py   # table metadata + optional FAISS shortlist
│   ├── column_metadata_retrieval.py # column candidates for selected tables; threshold + column FAISS
│   ├── relationship_retrieval.py     # FK rows from metadata JSON (API); DB list helper for build scripts
│   ├── fewshot_retrieval.py          # few_shot catalog JSON (+ optional DB fallback)
│   ├── sql_validator.py              # rule-based checks on generated SQL (Gen-SQL pipeline)
│   └── ...
└── api/                          # FastAPI app and routes
    ├── __init__.py
    ├── main.py                   # App entry point; mounts routers (uvicorn backend.api.main:app)
    ├── db.py                     # sessions (title, client_id, use_case), chat_messages, intent/table/column outputs, session_memory
    └── routes/                   # One module per agent/flow
        ├── __init__.py
        ├── query.py              # GET /use-cases, GET /sessions, GET /sessions/{id}/messages, POST /session, POST /query (full pipeline incl. Gen-SQL + validation)
        └── ...
```

## Conventions

- **Agents** live under `backend/agents/`. Each agent has a single entry point (e.g. `run_intent(user_message, use_case)`) and uses **services** and **config**.
- **Services** are reusable pieces (retrieval, LLM client, DB helpers) used by one or more agents. No agent-specific logic.
- **Config** (`backend/config.py`) holds env, paths, and constants. No business logic.
- **API:** The app lives in `backend/api/main.py` (not at backend root). To add more agents: add a new router in `api/routes/<name>.py` and `app.include_router(...)` in `main.py`. Keep one route module per flow (query = Intent, later sql = Gen-SQL).
- Run the app from **project root**: `uvicorn backend.api.main:app --reload`.

## Reference

- Chat UI, session APIs, `localStorage` keys: `docs/CHAT_UI_AND_SESSIONS.md`
- Multi-chat feature pointer: `docs/MULTI_CHAT_SIDEBAR_PLAN.md`
- Backfill session title / client_id: `docs/BACKFILL_SESSIONS.md`
- Supabase (hosted DB) from scratch: `docs/SUPABASE_SETUP.md`
- Stage 1 scope and order: `docs/STAGE1_FINALIZED_PLAN.md`
- Table Agent (5a) — metadata shortlist, LLM selection, DB, API, UI: `docs/TABLE_AGENT_5A_PLAN.md`
- Column Agent (5b) — column metadata, threshold/FAISS, LLM, DB, API: `docs/COLUMN_AGENT_5B_PLAN.md`
- Full agent architecture (Phase 3): see plan referenced there (e.g. phase_3_agent_architecture in .cursor/plans).
- FK relationships (per-domain `table_relationships`, extract, embeddings JSON, retrieval): `docs/RELATIONSHIPS_PIPELINE.md`.
