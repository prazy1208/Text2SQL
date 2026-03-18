# Stage 1 — Finalized Plan (No Code Yet)

Single reference plan for: business-rules FAISS build, app schema, Intent Agent, basic UI, and **intent_agent_output** for downstream. No code changes until you approve.

---

## 1. Scope

- **Basic UI:** Use case dropdown + query input + one output area (Intent output for now; SQL later).
- **Same database:** One DB (e.g. `text2sql_db`). New **app_schema** only for sessions and the **intent_agent_output** table. Business rules stay in **domain schemas** (already created).
- **Persistence:** Every request: create/reuse session, save one row in **intent_agent_output** with user_input, use_case, and each output in its own column (rephrased_question, keywords, business_insights).
- **First agent:** Intent Agent only (LLM rephrase + keywords; FAISS retrieval over business rules → 5–15 insights). Output standardized as **intent_agent_output** and passed on later.
- **Business rules embeddings:** FAISS + metadata store (same pattern as table metadata). Build script reads from existing business_rules tables, embeds, writes indexes and metadata.

---

## 2. Where Business Rules Live (Already in DB)

Per `Text2SQL_PostgreSQL_Setup_Guide.md`, rules are in **domain schemas**, not app_schema:

| Schema             | Table                      | Columns                                                                 |
|--------------------|----------------------------|-------------------------------------------------------------------------|
| healthcare_schema  | healthcare_business_rules | rule_id, concept_name, description, insight, keywords (TEXT[]), created_at |
| retail_schema      | retail_business_rules     | rule_id, concept_name, description, insight, keywords (TEXT[]), created_at |
| finance_schema     | finance_business_rules    | rule_id, concept_name, description, insight, keywords (TEXT[]), created_at |

- **No** app_schema.business_rules table. Build script and retrieval use these three tables.
- **Use case → schema/table:** healthcare → healthcare_schema.healthcare_business_rules; retail → retail_schema.retail_business_rules; finance → finance_schema.finance_business_rules.

---

## 3. App Schema (Same DB, New Schema)

- **Schema name:** `app_schema`.
- **Tables:** Only app/session data.

| Table                  | Purpose |
|------------------------|---------|
| **sessions**           | session_id (UUID), created_at [, updated_at]. |
| **intent_agent_output**| One row per user request; every Intent output in **separate columns** (see below). |

**Table `app_schema.intent_agent_output` — columns:**

| Column               | Type      | Purpose |
|----------------------|-----------|---------|
| id                   | SERIAL    | Primary key. |
| session_id           | UUID      | FK to sessions. |
| use_case             | VARCHAR   | healthcare / retail / finance. |
| user_input           | TEXT      | Original user message. |
| rephrased_question   | TEXT      | Intent output: clarified question. |
| keywords             | TEXT[]    | Intent output: extracted keywords (array of strings). |
| business_insights    | TEXT[]    | Intent output: retrieved insights (array of strings). |
| created_at           | TIMESTAMP | When the row was created. |

- The **intent_agent_output** table stores each Intent Agent result in **separate columns**. Downstream agents (Table, Column, Gen-SQL) read these columns for the same turn instead of re-running Intent.
- Single `DATABASE_URL`; tables referenced as `app_schema.sessions`, `app_schema.intent_agent_output`.

---

## 4. Intent Agent Output — Structure and Storage

**Purpose:** One canonical shape for the Intent Agent result. Stored in the **intent_agent_output** table in **separate columns** and returned by the API so later pipeline steps can use it without re-running Intent.

**Logical structure (for API and downstream agents):**

- **rephrased_question** (string): Clarified, machine-oriented version of the user question.
- **keywords** (list of strings): Extracted terms (e.g. "transaction volume", "sum", "merchant category", "top 5", "last month").
- **business_insights** (list of strings): 5–15 retrieved insight strings from the business-rules FAISS search (e.g. "Analyzing spend by merchant category…").

**Where it is stored:**

- In table **intent_agent_output**: three separate columns — **rephrased_question** (TEXT), **keywords** (TEXT[]), **business_insights** (TEXT[]) — for the row of that request.
- In **API response**: can be returned as an object (e.g. `intent_agent_output: { rephrased_question, keywords, business_insights }`) built from these columns for convenience.

**Downstream:** Table Agent, Column Agent, Few-Shot Agent, Gen-SQL Agent read rephrased_question, keywords, and business_insights (from the same intent_agent_output row or from the API payload); no need to call Intent again for the same turn.

---

## 5. Business Rules → FAISS and Metadata Store

**Source:** Existing tables `healthcare_schema.healthcare_business_rules`, `retail_schema.retail_business_rules`, `finance_schema.finance_business_rules`.

**Build script (to implement):**

1. Connect with existing `DATABASE_URL`.
2. For each schema (healthcare_schema, retail_schema, finance_schema):
   - SELECT rule_id, concept_name, description, insight, keywords, created_at from the corresponding table.
   - Build one **text per rule** for embedding: e.g. concatenate concept_name, description, insight, and keywords (array → string). That string is the “content” for that rule.
   - Embed all contents with **sentence-transformers** (all-MiniLM-L6-v2), same as `build_vector_store`.
   - Build **FAISS IndexFlatL2**, add vectors, write index to `faiss_indexes/business_rules_healthcare_schema.index` (and same for retail_schema, finance_schema).
   - Write **metadata** to `business_rules_store/healthcare_schema_rules.json` (and same for retail, finance). Each entry: index position → rule_id, concept_name, description, insight, keywords, and the combined “content” (so retrieval can return display text without hitting DB).

**Paths:**

- Indexes: `faiss_indexes/business_rules_healthcare_schema.index`, `business_rules_retail_schema.index`, `business_rules_finance_schema.index`.
- Metadata: `business_rules_store/healthcare_schema_rules.json`, `retail_schema_rules.json`, `finance_schema_rules.json`.
- Run script after any change to business rules (e.g. `python build_business_rules_vector_store.py`).

**Retrieval (at query time):**

- Given use_case, load the matching FAISS index and metadata file.
- Embed the (rephrased) user question with the same model.
- FAISS search top k (e.g. 5–15), map indices to metadata entries, return list of strings (e.g. description + insight or content) as **business_insights** inside **intent_agent_output**.

---

## 6. Intent Agent — Summary

- **Inputs:** user_message, use_case [, optional conversation_context later].
- **Outputs:** Exactly the **intent_agent_output** object: rephrased_question, keywords, business_insights.
- **Steps:** (1) LLM: rephrase user question and extract keywords. (2) FAISS retrieval over business rules for use_case → 5–15 insights. (3) Return structured intent_agent_output.
- **Storage:** API saves Intent Agent result to `app_schema.interactions` in separate columns: rephrased_question, keywords, business_insights; returns the same (e.g. as intent_agent_output object) to the client.

---

## 7. API Contract (Stage 1)

- **POST /query**  
  - Body: `{ "message": string, "use_case": string, "session_id": string | null }`.  
  - If session_id is null, create new session and return its id.  
  - Run Intent Agent; insert one row into **intent_agent_output**: session_id, use_case, user_input, rephrased_question, keywords, business_insights (separate columns).  
  - Response:  
    - `session_id`, `rephrased_question`, `keywords`, `business_insights` (and optionally wrapper key `intent_agent_output`), and `error` if something failed.

- **GET /use-cases** (optional): Return list of use cases for the dropdown.

---

## 8. Basic Frontend

- Use case selector (Healthcare / Retail / Finance).
- Query input (single field or textarea).
- Submit → POST /query with message, use_case, session_id (if any).
- Output area: show rephrased_question, keywords, business_insights. Later: show SQL or error.
- Session id can be stored in state or localStorage for future use.

---

## 9. Implementation Order (Final)

1. **App schema** — Create `app_schema` and tables `sessions`, **intent_agent_output**. Table **intent_agent_output** has columns: id, session_id, use_case, user_input, rephrased_question (TEXT), keywords (TEXT[]), business_insights (TEXT[]), created_at. No business_rules table in app_schema.
2. **Business-rules FAISS build script** — Read from healthcare/retail/finance business_rules tables; build combined text per rule; embed; write FAISS indexes and `business_rules_store/*.json`. Run once after DB has rules.
3. **Backend config** — PROJECT_ROOT, DATABASE_URL, APP_SCHEMA, paths to faiss_indexes and business_rules_store.
4. **Business-rules retrieval service** — Load index + metadata for use_case; embed query; FAISS search; return list of insight strings.
5. **LLM client and intent prompts** — Rephrase + keyword extraction.
6. **Intent Agent** — Assemble **intent_agent_output** (rephrased_question, keywords, business_insights) and return it.
7. **POST /query and persistence** — Create/get session; run Intent Agent; insert one row into **intent_agent_output** (rephrased_question, keywords, business_insights in separate columns); return session_id and the three output fields.
8. **Basic frontend** — Use case + query + submit + display rephrased_question, keywords, business_insights.

---

## 10. What This Plan Does Not Include Yet

- Conversation Agent (deferred).
- Cache Agent (deferred).
- Table Agent, Column Agent, Few-Shot Agent, Gen-SQL Agent, SQL Validator (later stages).
- Execution of SQL or results processing (later).

---

## 11. Reference to Other Plans

- **Project layout** (backend/agents, backend/services, config): see `PROJECT_STRUCTURE.md` in the project root. Use it to keep agents and services organized as Table, Column, Few-Shot, Gen-SQL, and SQL Validator agents are added.
- Full agent architecture (all agents, flow, Conversation deferred): `phase_3_agent_architecture_19e4c54c.plan.md` (in .cursor/plans or project).
- Previous Stage 1 draft with app_schema.business_rules: superseded by this document; business rules are in domain schemas per setup guide.

---

**End of finalized plan.** Proceed with code only after approval.
