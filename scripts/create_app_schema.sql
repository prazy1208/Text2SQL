-- App schema for Stage 1: sessions and intent_agent_output
-- Run against text2sql_db (e.g. in pgAdmin Query Tool or via run_create_app_schema.py)

-- Schema
CREATE SCHEMA IF NOT EXISTS app_schema;

-- Sessions: one row per conversation session
CREATE TABLE IF NOT EXISTS app_schema.sessions (
    session_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Intent agent output: one row per user request; each Intent output in separate columns
CREATE TABLE IF NOT EXISTS app_schema.intent_agent_output (
    id                 SERIAL PRIMARY KEY,
    session_id         UUID NOT NULL REFERENCES app_schema.sessions(session_id) ON DELETE CASCADE,
    use_case           VARCHAR(64) NOT NULL,
    user_input         TEXT NOT NULL,
    rephrased_question TEXT,
    keywords           TEXT[],
    business_insights  TEXT[],
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional: index for listing outputs by session
CREATE INDEX IF NOT EXISTS idx_intent_agent_output_session_id
    ON app_schema.intent_agent_output(session_id);

-- Optional: index for filtering by use_case
CREATE INDEX IF NOT EXISTS idx_intent_agent_output_use_case
    ON app_schema.intent_agent_output(use_case);

-- Table agent output: at most one row per intent row (FK intent_agent_output.id)
CREATE TABLE IF NOT EXISTS app_schema.table_agent_output (
    id                 SERIAL PRIMARY KEY,
    intent_output_id   INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    selected_tables    TEXT[] NOT NULL DEFAULT '{}',
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

COMMENT ON SCHEMA app_schema IS 'Application/session data for Text2SQL Stage 1';
COMMENT ON TABLE app_schema.sessions IS 'One row per chat session';
COMMENT ON TABLE app_schema.intent_agent_output IS 'One row per user query; stores Intent Agent output in separate columns';
COMMENT ON TABLE app_schema.table_agent_output IS 'Table Agent: selected_tables for one intent_agent_output row';

-- Few-shot agent output: at most one row per intent_agent_output row
CREATE TABLE IF NOT EXISTS app_schema.few_shot_agent_output (
    id                  SERIAL PRIMARY KEY,
    intent_output_id    INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    few_shot_examples   JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

COMMENT ON TABLE app_schema.few_shot_agent_output IS 'Few-Shot Agent: selected examples for one intent_agent_output row';

-- Column agent output: at most one row per table_agent_output row
CREATE TABLE IF NOT EXISTS app_schema.column_agent_output (
    id                      SERIAL PRIMARY KEY,
    table_agent_output_id   INT NOT NULL REFERENCES app_schema.table_agent_output(id) ON DELETE CASCADE,
    selected_columns        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (table_agent_output_id)
);

COMMENT ON TABLE app_schema.column_agent_output IS 'Column Agent: selected_columns (per table) for one table_agent_output row';

-- ---------------------------------------------------------------------------
-- Chat persistence (for chat-style UX + intent confirmation flow)
-- ---------------------------------------------------------------------------

-- One row per displayed chat message (user/assistant/system), per session.
CREATE TABLE IF NOT EXISTS app_schema.chat_messages (
    id            BIGSERIAL PRIMARY KEY,
    session_id    UUID NOT NULL REFERENCES app_schema.sessions(session_id) ON DELETE CASCADE,
    role          VARCHAR(16) NOT NULL,  -- 'user' | 'assistant' | 'system'
    message_type  VARCHAR(32) NOT NULL DEFAULT 'message', -- 'new_query' | 'intent_confirmation' | 'intent_correction' | etc.
    content       TEXT NOT NULL,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id_created_at
    ON app_schema.chat_messages(session_id, created_at);

COMMENT ON TABLE app_schema.chat_messages IS 'Session chat transcript (user/assistant/system messages)';

-- Records intent confidence + confirmation status for a given intent output.
CREATE TABLE IF NOT EXISTS app_schema.intent_review (
    id                     BIGSERIAL PRIMARY KEY,
    intent_output_id       INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    confidence_score       INT NOT NULL, -- 0..100
    confirmation_required  BOOLEAN NOT NULL DEFAULT FALSE,
    confirmation_status    VARCHAR(16) NOT NULL DEFAULT 'pending', -- 'pending' | 'confirmed' | 'rejected' | 'superseded'
    reviewed_at            TIMESTAMP WITH TIME ZONE,
    created_at             TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

CREATE INDEX IF NOT EXISTS idx_intent_review_status
    ON app_schema.intent_review(confirmation_status);

COMMENT ON TABLE app_schema.intent_review IS 'Intent confidence + user confirmation status for one intent_agent_output row';

-- Stores rolling summary for long conversations to keep prompts token-safe.
CREATE TABLE IF NOT EXISTS app_schema.session_memory (
    session_id                  UUID PRIMARY KEY REFERENCES app_schema.sessions(session_id) ON DELETE CASCADE,
    summary_json                JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_summarized_message_id  BIGINT,
    updated_at                  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE app_schema.session_memory IS 'Per-session structured summary for context-window + long chat memory';

-- Gen-SQL agent output: at most one row per intent_agent_output row
CREATE TABLE IF NOT EXISTS app_schema.gen_sql_agent_output (
    id                         SERIAL PRIMARY KEY,
    intent_output_id           INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    generated_sql              TEXT NOT NULL DEFAULT '',
    reasoning_summary          TEXT,
    validation_passed          BOOLEAN NOT NULL DEFAULT FALSE,
    validation_error_codes     TEXT NOT NULL DEFAULT '',
    validation_error_message   TEXT NOT NULL DEFAULT '',
    blocked_keywords           TEXT NOT NULL DEFAULT '',
    is_single_statement        BOOLEAN NOT NULL DEFAULT FALSE,
    is_select_only             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

COMMENT ON TABLE app_schema.gen_sql_agent_output IS 'Gen-SQL Agent: generated SQL and rule-based validation columns per intent_agent_output row';
