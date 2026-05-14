# 🔐 Privacy-Preserving Natural Language Querying via Schema-Driven Agent Pipelines

## 📌 Overview
This project enables **non-technical users** to explore data using natural language without ever exposing sensitive data to external systems.

Traditional natural language querying systems often rely on direct access to datasets, which introduces privacy risks. This project takes a fundamentally different approach:  

👉 **All query generation is performed using schema metadata only** (table names, column descriptions, relationships, and business context).  
👉 **No raw data is ever shared with Large Language Models (LLMs).**

By treating **privacy as a first-class constraint**, the system ensures safe and controlled query generation while maintaining usability and flexibility.

## 🧠 Key Idea: Schema-Only Reasoning
Instead of sending actual data to the model, the system uses:
- Table schemas  
- Column descriptions  
- Relationships between tables  
- Business context metadata  

This allows the LLM to:
- Understand user intent  
- Generate accurate structured queries  
- Maintain strict data privacy  

## ⚙️ Architecture

The system is built as an **LLM-powered, agent-driven pipeline** that decomposes the problem into modular stages:

### 🔄 Pipeline Stages
1. **Intent Interpretation**  
   - Understands the user's natural language query  

2. **Schema-Aware Table Selection**  
   - Identifies relevant tables using metadata  

3. **Column Selection & Filtering**  
   - Narrows down to required fields  

4. **Contextual Grounding**  
   - Uses validated examples and business logic  

5. **Structured Query Generation**  
   - Produces SQL (or equivalent structured query)

## 🏗️ Design Principles

### 🔐 Privacy First
- No raw data exposure at any stage  
- Schema-only interaction with LLMs  
- Safe for sensitive enterprise environments  

### 🔌 Execution-Agnostic
- Query generation is **decoupled from execution**

### 🧩 Modular Agent Design
- Each stage is handled by a dedicated agent  
- Improves interpretability and debugging  
- Enables independent optimization of components  

## ⏱️ Performance
- Handles **moderately complex analytical queries**
- End-to-end pipeline latency: **~30–50 seconds**

## 🧪 Data Usage
- Uses **synthetic or publicly available datasets only**
- No real or sensitive data is included in this project

## Documentation

| Document | Contents |
|----------|----------|
| [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) | Repository layout, backend conventions, how routes are organized |
| [docs/CHAT_UI_AND_SESSIONS.md](docs/CHAT_UI_AND_SESSIONS.md) | Multi-chat sidebar, session/chat REST API, Postgres fields, browser `localStorage` keys |
| [docs/MULTI_CHAT_SIDEBAR_PLAN.md](docs/MULTI_CHAT_SIDEBAR_PLAN.md) | Short status pointer for the multi-chat implementation |
| [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md) | Hosted Postgres (Supabase) connection and schema |

## Repository layout (summary)

- **`backend/`** — FastAPI entrypoint [`backend/api/main.py`](backend/api/main.py), agents under `backend/agents/`, shared services under `backend/services/`, HTTP routes under `backend/api/routes/` (including [`query.py`](backend/api/routes/query.py): `/query`, `/session`, `/sessions`, session messages).
- **`frontend/`** — Static chat UI (`index.html`, `app.js`, `styles.css`) served at `/`.
- **`scripts/`** — Database DDL such as [`scripts/create_app_schema.sql`](scripts/create_app_schema.sql).
- **`docs/`** — Setup guides and architecture notes.

## Running locally

From the project root (requires `.env` with `DATABASE_URL` and an LLM API key):

```bash
uvicorn backend.api.main:app --reload
```

Then open `http://127.0.0.1:8000/` for the chat UI. Apply `scripts/create_app_schema.sql` (or your full setup script) so `app_schema.sessions` and `chat_messages` exist.

Project URL: https://prazy1208-text2sql.hf.space/

## 🚀 Future Scope
- Introduce **caching mechanisms** to optimize repeated query performance  
- Extend **conversational memory** and structured persistence for richer reload fidelity  
- Refine **back-and-forth querying** (e.g. intent flows across session switches)  
