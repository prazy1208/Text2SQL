# Project structure

Layout for the Text2SQL backend and scripts. Keeps agents, services, and config organized as more agents are added (Table, Column, Few-Shot, Gen-SQL, SQL Validator).

## Root

```
Text2SQL project/
├── .env
├── PROJECT_STRUCTURE.md          # this file
├── STAGE1_FINALIZED_PLAN.md
├── requirements.txt
├── build_vector_store.py         # table/column metadata → FAISS + metadata_store
├── build_business_rules_vector_store.py   # business rules → FAISS + business_rules_store
├── generate_data.py
├── faiss_indexes/                # FAISS indexes (schema + business_rules_*)
├── metadata_store/               # table/column metadata JSON (per schema)
├── business_rules_store/         # business-rules metadata JSON (per schema)
├── backend/                      # API and pipeline
├── scripts/                      # one-off scripts (e.g. create_app_schema)
└── frontend/                     # Basic UI (Stage 1): index.html, styles.css, app.js; served at / by FastAPI
```

## Backend

```
backend/
├── __init__.py
├── config.py                     # PROJECT_ROOT, get_engine(), APP_SCHEMA, paths, USE_CASES
├── agents/                       # one module per agent
│   ├── __init__.py
│   ├── intent_agent.py           # Stage 1: rephrase + keywords + business_insights
│   │   # (later) table_agent.py, column_agent.py, few_shot_agent.py, gen_sql_agent.py, sql_validator.py
│   └── ...
├── services/                     # shared services used by agents
│   ├── __init__.py
│   ├── business_rules_retrieval.py   # FAISS retrieval → list of insight strings
│   │   # (later) llm_client.py, table_metadata_retrieval.py, etc.
│   └── ...
└── api/                          # FastAPI app and routes
    ├── __init__.py
    ├── main.py                   # App entry point; mounts routers (uvicorn backend.api.main:app)
    ├── db.py                     # Session + intent_agent_output persistence
    └── routes/                   # One module per agent/flow
        ├── __init__.py
        ├── query.py              # Intent Agent: GET /use-cases, POST /query
        └── ...                   # (later) sql.py for Gen-SQL, etc.
```

## Conventions

- **Agents** live under `backend/agents/`. Each agent has a single entry point (e.g. `run_intent(user_message, use_case)`) and uses **services** and **config**.
- **Services** are reusable pieces (retrieval, LLM client, DB helpers) used by one or more agents. No agent-specific logic.
- **Config** (`backend/config.py`) holds env, paths, and constants. No business logic.
- **API:** The app lives in `backend/api/main.py` (not at backend root). To add more agents: add a new router in `api/routes/<name>.py` and `app.include_router(...)` in `main.py`. Keep one route module per flow (query = Intent, later sql = Gen-SQL).
- Run the app from **project root**: `uvicorn backend.api.main:app --reload`.

## Reference

- Stage 1 scope and order: `STAGE1_FINALIZED_PLAN.md`
- Full agent architecture (Phase 3): see plan referenced there (e.g. phase_3_agent_architecture in .cursor/plans).
