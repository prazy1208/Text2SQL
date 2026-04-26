# Text2SQL Project - PostgreSQL & Healthcare Schema Setup Guide

------------------------------------------------------------------------

## 1. PostgreSQL Installation (Windows)

### Step 1: Download PostgreSQL

Download from official website:
https://www.postgresql.org/download/windows/

Use the EnterpriseDB installer.

------------------------------------------------------------------------

### Step 2: Install PostgreSQL

During installation:

-   Keep default port: **5432**
-   Set a secure password for user **postgres**
-   Keep default installation directory
-   You may uncheck **Stack Builder** (not required)

Finish installation.

------------------------------------------------------------------------

## 2. Add Server in pgAdmin 4

### Step 1: Open pgAdmin 4

Enter master password.

### Step 2: Register Server

Right click: Servers → Register → Server

### General Tab

-   Name: `text2sql_dev`

### Connection Tab

-   Host: `localhost`
-   Port: `5432`
-   Maintenance DB: `postgres`
-   Username: `postgres`
-   Password: (your password)
-   Check "Save Password"

Click Save.

------------------------------------------------------------------------

## 3. Create Project Database

Right click: Databases → Create → Database

-   Database Name: `text2sql_db`
-   Owner: `postgres`

Click Save.

------------------------------------------------------------------------

## 4. Create Healthcare Schema

Open Query Tool on `text2sql_db` and run:

``` sql
CREATE SCHEMA healthcare_schema;
```

Refresh Schemas to confirm creation.

------------------------------------------------------------------------

## 5. Create Healthcare Tables

Run the following SQL in Query Tool:

``` sql
-- =========================
-- PATIENTS TABLE
-- =========================
CREATE TABLE healthcare_schema.patients (
    patient_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(20),
    city VARCHAR(100),
    state VARCHAR(100),
    insurance_type VARCHAR(50),
    registration_date DATE
);

-- =========================
-- VISITS TABLE
-- =========================
CREATE TABLE healthcare_schema.visits (
    visit_id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES healthcare_schema.patients(patient_id),
    admission_date DATE,
    discharge_date DATE,
    department VARCHAR(100),
    visit_type VARCHAR(50),
    total_cost NUMERIC(12,2)
);

-- =========================
-- DIAGNOSES TABLE
-- =========================
CREATE TABLE healthcare_schema.diagnoses (
    diagnosis_id SERIAL PRIMARY KEY,
    visit_id INT REFERENCES healthcare_schema.visits(visit_id),
    diagnosis_code VARCHAR(20),
    diagnosis_description VARCHAR(255),
    severity_level VARCHAR(20)
);
```

------------------------------------------------------------------------

## 6. Validate Tables

Run:

``` sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'healthcare_schema';
```

Expected Output: - patients - visits - diagnoses

------------------------------------------------------------------------

## 7. Create App Schema (Stage 1)

The **app_schema** holds application and session data for the Text2SQL pipeline (Stage 1): **sessions**, **intent_agent_output** (Intent Agent: rephrased question, keywords, business insights), and **table_agent_output** (Table Agent: `selected_tables` linked to `intent_agent_output.id`). Fresh installs use `scripts/create_app_schema.sql` (includes all three). Existing databases created before Table Agent: run `scripts/migration_add_table_agent_output.sql` once.

**Option A — Run SQL in pgAdmin**

Open Query Tool on **text2sql_db** and run the following (or run the file `scripts/create_app_schema.sql`):

```sql
-- App schema: sessions, intent_agent_output, table_agent_output (same as scripts/create_app_schema.sql)
CREATE SCHEMA IF NOT EXISTS app_schema;

CREATE TABLE IF NOT EXISTS app_schema.sessions (
    session_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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

CREATE INDEX IF NOT EXISTS idx_intent_agent_output_session_id
    ON app_schema.intent_agent_output(session_id);
CREATE INDEX IF NOT EXISTS idx_intent_agent_output_use_case
    ON app_schema.intent_agent_output(use_case);

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
```

**Option B — Run the Python script**

From the project root, with `.env` configured (e.g. `DATABASE_URL` or `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`):

```bash
python scripts/run_create_app_schema.py
```

The script uses the same database settings as `build_vector_store.py` and creates `app_schema`, `sessions`, `intent_agent_output`, and `table_agent_output` in **text2sql_db**.

------------------------------------------------------------------------

## 7b. Legacy rollback: `system_schema.table_relationships` (optional)

If you previously created the **centralized** FK metadata table under `system_schema` (older project scripts that are no longer in the repo), remove it before adopting **per-domain** `table_relationships` tables in each business schema. Run once on **text2sql_db** as superuser or owner:

```sql
DROP TABLE IF EXISTS system_schema.table_relationships;
-- Optional: only if nothing else should live in system_schema
-- DROP SCHEMA IF EXISTS system_schema CASCADE;
```

If other objects still use `system_schema`, omit `DROP SCHEMA` and only drop the table.

------------------------------------------------------------------------

## 7c. Domain schemas — FK metadata (`table_relationships`)

**Runtime (`POST /query`):** FK edges are read from **`metadata_store/relationships_{schema}_metadata.json`** (`list_relationships_from_metadata`). Regenerate those files after changing the database: `python build_relationship_embeddings.py`. **Postgres `table_relationships` tables** are still required for `extract_and_load_relationships.py` and the embedding build; create/load them as below if rows are missing or stale.

After `healthcare_schema`, `retail_schema`, and `finance_schema` exist, add one **`table_relationships`** table per domain schema (referencing side is always in that domain; `target_schema` holds the referenced table’s schema for cross-schema FKs).

### One-command refresh (recommended after schema/table changes)

From project root, run:

```bash
python scripts/run_full_schema_refresh.py
```

This runs the full refresh pipeline in order:
1. Applies `scripts/create_domain_schemas.sql` (domain tables + comments + safe alter/constraint updates).
2. Ensures domain `table_relationships` tables exist.
3. Extracts FK relationships from `pg_catalog` and upserts into domain `table_relationships`.
4. Rebuilds relationship metadata JSON:
   - `metadata_store/relationships_healthcare_schema_metadata.json`
   - `metadata_store/relationships_retail_schema_metadata.json`
   - `metadata_store/relationships_finance_schema_metadata.json`
5. Rebuilds domain metadata + FAISS indexes:
   - `metadata_store/{schema}_metadata.json`
   - `metadata_store/{schema}_columns_metadata.json`
   - `faiss_indexes/{schema}.index`
   - `faiss_indexes/{schema}_columns.index`

### One-shot setup (recommended for new databases)

Run the full script in the **Supabase SQL Editor** (or pgAdmin against your DB): `scripts/complete_setup.sql`. It creates domain tables, `app_schema`, and **all three** `table_relationships` tables in one go. Safe to re-run: DDL uses `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`.

### If you already ran an older `complete_setup.sql` without FK tables

Apply only the FK block using either:

**Option A — SQL file**

Run `scripts/create_domain_schema_table_relationships.sql` in the SQL editor (same DDL as the FK section at the end of `complete_setup.sql`), or:

**Option B — Migration file**

Run `scripts/migration_add_domain_schema_table_relationships.sql` once (equivalent `CREATE TABLE IF NOT EXISTS`).

**Option C — Python**

From project root with `.env` pointing at the database:

```bash
python scripts/run_create_domain_schema_table_relationships.py
```

### Load rows from actual foreign keys

Empty `table_relationships` tables are not enough: populate them from `pg_catalog` so each row has `relationship_text` for the LLM.

```bash
python scripts/extract_and_load_relationships.py
```

Requires the domain business tables and FK constraints to exist (e.g. `retail_schema.orders` → `customers`, `products`). After loading, `POST /query` with `use_case: retail` will load `retail_schema.table_relationships`.

### Optional: embeddings JSON

Precompute vectors for each `relationship_text` and write `metadata_store/relationships_{schema}_metadata.json`:

```bash
python build_relationship_embeddings.py
```

------------------------------------------------------------------------

## Architecture Summary

Database: PostgreSQL\
Schema: healthcare_schema\
Tables: - patients - visits - diagnoses

This structure supports: - JOIN operations - Aggregations - Time-based
filtering - Cost analysis - Severity filtering - Multi-table reasoning
for Text-to-SQL system

------------------------------------------------------------------------

# Create Retail Schema

```sql
CREATE SCHEMA retail_schema;
```

# Create Retail Tables
Run the following SQL in Query Tool:

``` sql
-- =========================
-- CUSTOMERS TABLE
-- =========================
CREATE TABLE retail_schema.customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(150),
    city VARCHAR(100),
    state VARCHAR(100),
    signup_date DATE
);

-- =========================
-- PRODUCTS TABLE
-- =========================
CREATE TABLE retail_schema.products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(150),
    category VARCHAR(100),
    brand VARCHAR(100),
    price NUMERIC(10,2),
    launch_date DATE
);

-- =========================
-- ORDERS TABLE
-- =========================
CREATE TABLE retail_schema.orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES retail_schema.customers(customer_id),
    product_id INT REFERENCES retail_schema.products(product_id),
    order_date DATE,
    quantity INT,
    total_amount NUMERIC(12,2)
);
```
-----------------------------------------------

# Create Finance Schema

```sql
CREATE SCHEMA finance_schema;
```

# Create Finance Tables
Run the following SQL in Query Tool:

``` sql
-- =========================
-- ACCOUNTS TABLE
-- =========================
CREATE TABLE finance_schema.accounts (
    account_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(150),
    account_type VARCHAR(50), -- savings, checking
    branch_city VARCHAR(100),
    opening_date DATE,
    current_balance NUMERIC(14,2)
);

-- =========================
-- TRANSACTIONS TABLE
-- =========================
CREATE TABLE finance_schema.transactions (
    transaction_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES finance_schema.accounts(account_id),
    transaction_date DATE,
    transaction_type VARCHAR(50), -- debit, credit
    amount NUMERIC(14,2),
    description VARCHAR(255)
);

-- =========================
-- LOANS TABLE
-- =========================
CREATE TABLE finance_schema.loans (
    loan_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES finance_schema.accounts(account_id),
    loan_type VARCHAR(100), -- home, auto, personal
    loan_amount NUMERIC(14,2),
    interest_rate NUMERIC(5,2),
    loan_start_date DATE,
    loan_end_date DATE
);
```
```sql
-- =========================================
-- SCHEMA DESCRIPTION
-- =========================================
COMMENT ON SCHEMA healthcare_schema IS
'Contains healthcare operational data including patient demographics, hospital visits, and medical diagnoses for analytical and reporting purposes.';


-- =========================================
-- PATIENTS TABLE DESCRIPTION
-- =========================================
COMMENT ON TABLE healthcare_schema.patients IS
'Stores demographic and registration details of patients receiving healthcare services.';

COMMENT ON COLUMN healthcare_schema.patients.patient_id IS
'Unique system-generated identifier assigned to each patient.';

COMMENT ON COLUMN healthcare_schema.patients.first_name IS
'Patient''s legal first name.';

COMMENT ON COLUMN healthcare_schema.patients.last_name IS
'Patient''s legal last name.';

COMMENT ON COLUMN healthcare_schema.patients.date_of_birth IS
'Date of birth of the patient used for age-based analysis and eligibility checks.';

COMMENT ON COLUMN healthcare_schema.patients.gender IS
'Self-reported gender of the patient.';

COMMENT ON COLUMN healthcare_schema.patients.city IS
'City of residence of the patient.';

COMMENT ON COLUMN healthcare_schema.patients.state IS
'State of residence of the patient.';

COMMENT ON COLUMN healthcare_schema.patients.insurance_type IS
'Type of insurance coverage used by the patient (e.g., private, government, uninsured).';

COMMENT ON COLUMN healthcare_schema.patients.registration_date IS
'Date when the patient was first registered in the healthcare system.';


-- =========================================
-- VISITS TABLE DESCRIPTION
-- =========================================
COMMENT ON TABLE healthcare_schema.visits IS
'Records individual hospital or clinic visits made by patients, including department, visit type, and associated costs.';

COMMENT ON COLUMN healthcare_schema.visits.visit_id IS
'Unique system-generated identifier for each patient visit.';

COMMENT ON COLUMN healthcare_schema.visits.patient_id IS
'Foreign key referencing the patient who attended the visit.';

COMMENT ON COLUMN healthcare_schema.visits.admission_date IS
'Date when the patient was admitted for the visit.';

COMMENT ON COLUMN healthcare_schema.visits.discharge_date IS
'Date when the patient was discharged from the visit.';

COMMENT ON COLUMN healthcare_schema.visits.department IS
'Medical department responsible for the visit (e.g., cardiology, emergency, oncology).';

COMMENT ON COLUMN healthcare_schema.visits.visit_type IS
'Classification of visit such as inpatient, outpatient, or emergency.';

COMMENT ON COLUMN healthcare_schema.visits.total_cost IS
'Total billed cost associated with the visit, including treatments and services.';


-- =========================================
-- DIAGNOSES TABLE DESCRIPTION
-- =========================================
COMMENT ON TABLE healthcare_schema.diagnoses IS
'Stores medical diagnoses assigned during patient visits, including severity and diagnostic codes.';

COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_id IS
'Unique system-generated identifier for each diagnosis record.';

COMMENT ON COLUMN healthcare_schema.diagnoses.visit_id IS
'Foreign key referencing the visit during which the diagnosis was made.';

COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_code IS
'Standardized medical diagnosis code (e.g., ICD code) representing the condition.';

COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_description IS
'Textual description of the diagnosed medical condition.';

COMMENT ON COLUMN healthcare_schema.diagnoses.severity_level IS
'Indicates the severity of the diagnosed condition (e.g., mild, moderate, severe).';

-- =========================================
-- SCHEMA DESCRIPTION
-- =========================================
COMMENT ON SCHEMA retail_schema IS
'Contains retail business data including customer profiles, product catalog information, and sales transaction records for analytics and reporting.';


-- =========================================
-- CUSTOMERS TABLE DESCRIPTION
-- =========================================
COMMENT ON TABLE retail_schema.customers IS
'Stores customer demographic and account information for individuals who purchase products.';

COMMENT ON COLUMN retail_schema.customers.customer_id IS
'Unique system-generated identifier assigned to each customer.';

COMMENT ON COLUMN retail_schema.customers.first_name IS
'Customer''s first name as provided during registration.';

COMMENT ON COLUMN retail_schema.customers.last_name IS
'Customer''s last name as provided during registration.';

COMMENT ON COLUMN retail_schema.customers.email IS
'Registered email address used for communication, promotions, and order notifications.';

COMMENT ON COLUMN retail_schema.customers.city IS
'City where the customer resides.';

COMMENT ON COLUMN retail_schema.customers.state IS
'State where the customer resides.';

COMMENT ON COLUMN retail_schema.customers.signup_date IS
'Date when the customer created their account in the retail system.';


-- =========================================
-- PRODUCTS TABLE DESCRIPTION
-- =========================================
COMMENT ON TABLE retail_schema.products IS
'Stores product catalog information including category, brand, pricing, and launch details.';

COMMENT ON COLUMN retail_schema.products.product_id IS
'Unique system-generated identifier assigned to each product.';

COMMENT ON COLUMN retail_schema.products.product_name IS
'Official name of the product available for sale.';

COMMENT ON COLUMN retail_schema.products.category IS
'Product category used for grouping similar items (e.g., electronics, apparel, home goods).';

COMMENT ON COLUMN retail_schema.products.brand IS
'Brand or manufacturer associated with the product.';

COMMENT ON COLUMN retail_schema.products.price IS
'Current selling price of the product per unit.';

COMMENT ON COLUMN retail_schema.products.launch_date IS
'Date when the product was first introduced to the market.';


-- =========================================
-- ORDERS TABLE DESCRIPTION
-- =========================================
COMMENT ON TABLE retail_schema.orders IS
'Records customer purchase transactions including product ordered, quantity, and total transaction value.';

COMMENT ON COLUMN retail_schema.orders.order_id IS
'Unique system-generated identifier for each customer order.';

COMMENT ON COLUMN retail_schema.orders.customer_id IS
'Foreign key referencing the customer who placed the order.';

COMMENT ON COLUMN retail_schema.orders.product_id IS
'Foreign key referencing the product that was purchased.';

COMMENT ON COLUMN retail_schema.orders.order_date IS
'Date when the order was placed by the customer.';

COMMENT ON COLUMN retail_schema.orders.quantity IS
'Number of units of the product purchased in the order.';

COMMENT ON COLUMN retail_schema.orders.total_amount IS
'Total monetary value of the order calculated as quantity multiplied by unit price.';

-- =========================================
-- SCHEMA DESCRIPTION
-- =========================================
COMMENT ON SCHEMA finance_schema IS
'Contains financial services data including customer accounts, banking transactions, and loan records for operational reporting and financial analytics.';


-- =========================================
-- ACCOUNTS TABLE DESCRIPTION
-- =========================================
COMMENT ON TABLE finance_schema.accounts IS
'Stores customer bank account information including account type, branch location, and current balance.';

COMMENT ON COLUMN finance_schema.accounts.account_id IS
'Unique system-generated identifier assigned to each bank account.';

COMMENT ON COLUMN finance_schema.accounts.customer_name IS
'Full name of the customer who owns the bank account.';

COMMENT ON COLUMN finance_schema.accounts.account_type IS
'Type of bank account such as savings or checking.';

COMMENT ON COLUMN finance_schema.accounts.branch_city IS
'City where the bank branch managing the account is located.';

COMMENT ON COLUMN finance_schema.accounts.opening_date IS
'Date when the bank account was opened.';

COMMENT ON COLUMN finance_schema.accounts.current_balance IS
'Current available balance in the account.';


-- =========================================
-- TRANSACTIONS TABLE DESCRIPTION
-- =========================================
COMMENT ON TABLE finance_schema.transactions IS
'Records financial transactions performed on customer accounts including debits and credits.';

COMMENT ON COLUMN finance_schema.transactions.transaction_id IS
'Unique system-generated identifier for each transaction.';

COMMENT ON COLUMN finance_schema.transactions.account_id IS
'Foreign key referencing the account on which the transaction occurred.';

COMMENT ON COLUMN finance_schema.transactions.transaction_date IS
'Date when the transaction was executed.';

COMMENT ON COLUMN finance_schema.transactions.transaction_type IS
'Type of transaction such as debit (money withdrawn) or credit (money deposited).';

COMMENT ON COLUMN finance_schema.transactions.amount IS
'Monetary value of the transaction.';

COMMENT ON COLUMN finance_schema.transactions.description IS
'Short textual explanation describing the purpose or nature of the transaction.';


-- =========================================
-- LOANS TABLE DESCRIPTION
-- =========================================
COMMENT ON TABLE finance_schema.loans IS
'Stores loan account information associated with customer accounts including loan type, principal amount, and repayment terms.';

COMMENT ON COLUMN finance_schema.loans.loan_id IS
'Unique system-generated identifier for each loan record.';

COMMENT ON COLUMN finance_schema.loans.account_id IS
'Foreign key referencing the account associated with the loan.';

COMMENT ON COLUMN finance_schema.loans.loan_type IS
'Category of loan such as home loan, auto loan, or personal loan.';

COMMENT ON COLUMN finance_schema.loans.loan_amount IS
'Total principal amount borrowed under the loan agreement.';

COMMENT ON COLUMN finance_schema.loans.interest_rate IS
'Annual interest rate applied to the loan expressed as a percentage.';

COMMENT ON COLUMN finance_schema.loans.loan_start_date IS
'Date when the loan repayment period began.';

COMMENT ON COLUMN finance_schema.loans.loan_end_date IS
'Date when the loan is scheduled to be fully repaid.';


```

# Business rules for retail schema

```sql
CREATE TABLE retail_schema.retail_business_rules (
    rule_id SERIAL PRIMARY KEY,
    concept_name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    insight TEXT,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE retail_schema.retail_business_rules IS
'Stores domain-level business knowledge used by the Intent Agent to interpret user queries. 
The rules describe analytical business concepts related to the retail domain in natural language. 
They intentionally avoid references to database tables, columns, or SQL logic to prevent biasing 
downstream agents responsible for schema selection and SQL generation.';

COMMENT ON COLUMN retail_schema.retail_business_rules.rule_id IS
'Unique identifier for each business rule.';

COMMENT ON COLUMN retail_schema.retail_business_rules.concept_name IS
'High-level business concept represented by the rule, such as customer acquisition, product demand, or sales trends.';

COMMENT ON COLUMN retail_schema.retail_business_rules.description IS
'Neutral explanation of the business concept in natural language. 
This field defines the concept without referencing database schema, tables, columns, or SQL logic.';

COMMENT ON COLUMN retail_schema.retail_business_rules.insight IS
'Business reasoning that explains why the concept is important for analytical use cases.';

COMMENT ON COLUMN retail_schema.retail_business_rules.keywords IS
'List of keywords or phrases associated with the business concept. 
These keywords help semantic retrieval systems match user queries with relevant business rules.';

COMMENT ON COLUMN retail_schema.retail_business_rules.created_at IS
'Timestamp indicating when the business rule was created. Useful for rule governance and auditing.';

INSERT INTO retail_schema.retail_business_rules
(concept_name, description, insight, keywords)
VALUES

(
'Customer Acquisition',
'Customer acquisition refers to the process of gaining new customers who begin interacting with the business.',
'Tracking acquisition helps businesses understand growth and evaluate outreach or marketing efforts.',
ARRAY['new customers','customer growth','customer signup','customer acquisition']
),

(
'Customer Base Distribution',
'Customer base distribution describes how customers are spread across different geographic locations.',
'Understanding where customers are concentrated helps businesses identify strong markets and areas for expansion.',
ARRAY['customer location','customer regions','geographic distribution','customers by region']
),

(
'Customer Growth Trends',
'Customer growth trends represent how the number of customers changes over time.',
'Analyzing these trends helps businesses measure long-term growth and customer adoption.',
ARRAY['customer trends','customer increase','customer growth over time']
),

(
'Customer Engagement',
'Customer engagement reflects how actively customers interact with the business through purchasing behavior.',
'Understanding engagement levels helps identify loyal customers and overall customer activity.',
ARRAY['customer engagement','customer activity','active customers']
),

(
'Customer Purchase Behavior',
'Customer purchase behavior describes patterns in how customers buy products over time.',
'Studying purchasing patterns helps businesses understand customer preferences and buying habits.',
ARRAY['purchase behavior','customer buying patterns','shopping behavior']
),

(
'Product Catalog Overview',
'Product catalog analysis focuses on understanding the variety and organization of products offered by a business.',
'Reviewing the product catalog helps businesses maintain balanced offerings across categories and brands.',
ARRAY['product catalog','product list','available products']
),

(
'Product Category Analysis',
'Product categories group similar products together to simplify product organization and analysis.',
'Analyzing categories helps businesses understand demand patterns across different product types.',
ARRAY['product category','product categories','category analysis']
),

(
'Brand Representation',
'Brand representation reflects how different brands appear within the product assortment.',
'Understanding brand presence helps businesses evaluate brand diversity and popularity.',
ARRAY['brand presence','brand distribution','brand representation']
),

(
'Product Popularity',
'Product popularity reflects the level of interest customers show in particular products.',
'Popularity insights help businesses identify products that consistently attract customer attention.',
ARRAY['popular products','trending products','product interest']
),

(
'Product Introduction Trends',
'Product introduction trends describe how frequently new products are added to the catalog.',
'Monitoring product introductions helps businesses understand innovation and catalog expansion.',
ARRAY['new products','product launch','recent products']
),

(
'Sales Activity',
'Sales activity represents the overall purchasing interactions occurring between customers and the business.',
'Monitoring activity levels helps businesses evaluate demand and operational performance.',
ARRAY['sales activity','transactions','purchase activity']
),

(
'Order Volume',
'Order volume reflects the number of purchasing transactions occurring within a given timeframe.',
'Tracking order volume helps businesses understand changes in purchasing frequency.',
ARRAY['order volume','transaction count','number of purchases']
),

(
'Sales Trends',
'Sales trends describe how purchasing activity evolves across different time periods.',
'Trend analysis helps identify growth patterns and seasonal behavior.',
ARRAY['sales trends','purchase trends','transaction trends']
),

(
'Customer Purchasing Distribution',
'Customer purchasing distribution describes how purchasing activity varies among different customers.',
'Understanding purchasing distribution helps identify customers with higher engagement levels.',
ARRAY['customer spending','top customers','customer purchase activity']
),

(
'Product Demand Patterns',
'Product demand patterns describe how frequently different products attract customer purchases.',
'Understanding demand patterns helps businesses recognize products that drive consistent interest.',
ARRAY['product demand','high demand products','frequently purchased products']
),

(
'Product Category Demand',
'Category demand analysis evaluates how customer interest varies across different product categories.',
'This analysis helps businesses determine which types of products attract the most attention.',
ARRAY['category demand','popular categories','category interest']
),

(
'Brand Interest',
'Brand interest reflects the level of customer attention or engagement associated with particular brands.',
'Analyzing brand interest helps businesses understand which brands resonate most with customers.',
ARRAY['brand interest','popular brands','brand popularity']
),

(
'Customer Activity Over Time',
'Customer activity over time measures how purchasing engagement changes across different time periods.',
'Observing activity patterns helps identify periods of high or low customer interaction.',
ARRAY['customer activity trends','shopping activity','purchase timing']
);

```

# business rules for financial business rules

```sql

CREATE TABLE finance_schema.finance_business_rules (
    rule_id SERIAL PRIMARY KEY,
    concept_name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    insight TEXT,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE finance_schema.finance_business_rules IS
'Stores domain-level financial business knowledge used by the Intent Agent to interpret user queries. 
These rules describe financial analytical concepts and insights in natural language. 
They intentionally avoid referencing database tables, columns, or SQL logic in order to prevent 
biasing downstream agents responsible for schema selection and SQL generation.';

COMMENT ON COLUMN finance_schema.finance_business_rules.rule_id IS
'Unique identifier assigned to each financial business rule.';

COMMENT ON COLUMN finance_schema.finance_business_rules.concept_name IS
'High-level financial concept or analytical theme represented by the rule, such as transaction activity, financial trends, or spending patterns.';

COMMENT ON COLUMN finance_schema.finance_business_rules.description IS
'Neutral natural-language explanation of the financial concept. 
This field describes the concept without referencing database schema elements, implementation details, or SQL logic.';

COMMENT ON COLUMN finance_schema.finance_business_rules.insight IS
'Business insight explaining why the financial concept is important for analysis and decision-making.';

COMMENT ON COLUMN finance_schema.finance_business_rules.keywords IS
'List of keywords or phrases associated with the financial concept. 
These keywords help semantic retrieval systems match user queries with relevant business rules.';

COMMENT ON COLUMN finance_schema.finance_business_rules.created_at IS
'Timestamp indicating when the financial business rule was created. 
This supports governance, auditing, and lifecycle management of rules.';

INSERT INTO finance_schema.finance_business_rules
(concept_name, description, insight, keywords)
VALUES

(
'Transaction Activity',
'Transaction activity represents the overall movement of financial operations occurring within a system.',
'Monitoring transaction activity helps organizations understand operational intensity and financial usage patterns.',
ARRAY['transactions','transaction activity','financial activity']
),

(
'Transaction Volume Trends',
'Transaction volume trends describe how the number of financial transactions changes over time.',
'Analyzing transaction volume helps identify periods of increased financial activity or operational demand.',
ARRAY['transaction trends','transaction volume','transaction increase']
),

(
'Account Activity',
'Account activity reflects how actively financial accounts are used for transactions or operations.',
'Understanding account activity helps identify frequently used accounts and engagement patterns.',
ARRAY['account activity','active accounts','account usage']
),

(
'Account Distribution',
'Account distribution describes how accounts are organized or spread across different categories or groups.',
'Analyzing distribution helps organizations understand structural patterns within the financial system.',
ARRAY['account distribution','account categories','account groups']
),

(
'Financial Flow Analysis',
'Financial flow analysis examines how value moves across the financial system through transactions.',
'Understanding flow patterns helps identify major channels of financial movement.',
ARRAY['financial flow','money movement','transaction flow']
),

(
'Spending Patterns',
'Spending patterns describe how financial resources are utilized across various activities.',
'Analyzing spending behavior helps organizations identify common expenditure trends.',
ARRAY['spending patterns','financial spending','expense behavior']
),

(
'Revenue Activity',
'Revenue activity represents financial inflows generated through operational or business activities.',
'Monitoring revenue activity helps organizations track financial performance over time.',
ARRAY['revenue activity','income generation','financial inflow']
),

(
'Expense Activity',
'Expense activity reflects financial outflows resulting from operational or business expenditures.',
'Tracking expense patterns helps organizations understand cost distribution and spending behavior.',
ARRAY['expenses','cost activity','financial outflow']
),

(
'Financial Balance Monitoring',
'Balance monitoring focuses on tracking the financial position of accounts or entities over time.',
'Understanding balance patterns helps identify financial stability and resource availability.',
ARRAY['balance monitoring','account balances','financial position']
),

(
'Customer Financial Behavior',
'Customer financial behavior reflects how customers interact with financial services or perform financial operations.',
'Studying financial behavior helps organizations understand customer engagement with financial systems.',
ARRAY['financial behavior','customer transactions','customer financial activity']
),

(
'Transaction Frequency',
'Transaction frequency measures how often financial operations occur within a defined period.',
'Monitoring frequency helps organizations detect changes in system usage patterns.',
ARRAY['transaction frequency','transaction rate','financial operations']
),

(
'Financial Activity Distribution',
'Financial activity distribution describes how financial operations are spread across different entities or accounts.',
'Understanding distribution helps identify concentration of financial activity.',
ARRAY['financial distribution','activity spread','transaction concentration']
),

(
'Financial Trends Over Time',
'Financial trends describe how financial activity evolves across different time periods.',
'Trend analysis helps organizations identify growth patterns and financial cycles.',
ARRAY['financial trends','transaction trends','activity trends']
),

(
'High Activity Entities',
'High activity entities represent accounts or participants that show elevated levels of financial operations.',
'Identifying high activity entities helps organizations monitor major contributors to financial activity.',
ARRAY['high activity accounts','active entities','frequent transactions']
),

(
'Financial Participation',
'Financial participation reflects how widely financial services or operations are used among participants.',
'Analyzing participation helps understand adoption and engagement levels.',
ARRAY['financial participation','system usage','participant activity']
),

(
'Financial Growth Patterns',
'Financial growth patterns describe increases or decreases in financial activity levels over time.',
'Understanding growth patterns helps organizations assess expansion or contraction in operations.',
ARRAY['financial growth','activity growth','transaction growth']
),

(
'Operational Financial Insights',
'Operational financial insights focus on understanding the behavior and structure of financial operations within a system.',
'These insights help organizations make informed decisions about financial management and operational efficiency.',
ARRAY['financial insights','operational finance','financial analytics']
);

```

# Business rules for Healthcare schema

```sql

-- ============================================
-- CREATE HEALTHCARE BUSINESS RULES TABLE
-- ============================================

CREATE TABLE healthcare_schema.healthcare_business_rules (
    rule_id SERIAL PRIMARY KEY,
    concept_name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    insight TEXT,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE COMMENT
-- ============================================

COMMENT ON TABLE healthcare_schema.healthcare_business_rules IS
'Stores healthcare domain business knowledge used by the Intent Agent to interpret user queries. 
The rules describe healthcare analytical concepts and insights in natural language. 
They intentionally avoid referencing database tables, columns, or SQL logic to prevent 
biasing downstream agents responsible for schema selection and SQL generation.';

-- ============================================
-- COLUMN COMMENTS
-- ============================================

COMMENT ON COLUMN healthcare_schema.healthcare_business_rules.rule_id IS
'Unique identifier assigned to each healthcare business rule.';

COMMENT ON COLUMN healthcare_schema.healthcare_business_rules.concept_name IS
'High-level healthcare concept or analytical theme represented by the rule, such as patient activity, treatment patterns, or healthcare service utilization.';

COMMENT ON COLUMN healthcare_schema.healthcare_business_rules.description IS
'Neutral natural-language explanation of the healthcare concept. 
This field describes the concept without referencing database schema elements, implementation details, or SQL logic.';

COMMENT ON COLUMN healthcare_schema.healthcare_business_rules.insight IS
'Healthcare insight explaining why the concept is important for analysis, reporting, or operational understanding.';

COMMENT ON COLUMN healthcare_schema.healthcare_business_rules.keywords IS
'List of keywords or phrases associated with the healthcare concept. 
These keywords help semantic retrieval systems match user queries with relevant business rules.';

COMMENT ON COLUMN healthcare_schema.healthcare_business_rules.created_at IS
'Timestamp indicating when the healthcare business rule was created. 
Useful for governance, auditing, and lifecycle management.';

-- ============================================
-- INSERT HEALTHCARE BUSINESS RULES
-- ============================================

INSERT INTO healthcare_schema.healthcare_business_rules
(concept_name, description, insight, keywords)
VALUES

(
'Patient Registration Activity',
'Patient registration activity reflects how new patients begin interacting with healthcare services.',
'Monitoring registration patterns helps healthcare providers understand patient intake trends and service demand.',
ARRAY['new patients','patient registration','patient intake','patient enrollment']
),

(
'Patient Demographic Distribution',
'Patient demographic distribution describes how patients are represented across different demographic characteristics.',
'Understanding demographic distribution helps healthcare organizations identify the populations they serve.',
ARRAY['patient demographics','patient distribution','demographic analysis']
),

(
'Patient Visit Activity',
'Patient visit activity represents how frequently patients interact with healthcare providers through appointments or consultations.',
'Tracking visit activity helps healthcare providers understand service utilization patterns.',
ARRAY['patient visits','appointments','consultations','visit frequency']
),

(
'Healthcare Service Utilization',
'Healthcare service utilization reflects how healthcare services are used by patients across the organization.',
'Analyzing service utilization helps identify which services are most frequently accessed.',
ARRAY['service usage','healthcare utilization','medical services']
),

(
'Treatment Patterns',
'Treatment patterns describe how different treatments or medical procedures are provided to patients.',
'Understanding treatment patterns helps healthcare organizations evaluate care delivery practices.',
ARRAY['treatment patterns','medical procedures','patient treatment']
),

(
'Patient Care Activity',
'Patient care activity reflects the range of interactions between healthcare providers and patients during care delivery.',
'Monitoring care activity helps organizations understand healthcare workload and service delivery levels.',
ARRAY['patient care','care activity','medical care interactions']
),

(
'Patient Health Trends',
'Patient health trends describe how patient-related health activities evolve over time.',
'Tracking trends helps healthcare providers understand changes in care demand and treatment needs.',
ARRAY['health trends','patient health patterns','health activity trends']
),

(
'Healthcare Provider Activity',
'Healthcare provider activity reflects the level of engagement healthcare professionals have in delivering patient care.',
'Analyzing provider activity helps healthcare organizations understand workload distribution and service capacity.',
ARRAY['provider activity','medical staff activity','clinical workload']
),

(
'Appointment Patterns',
'Appointment patterns describe how patients schedule and attend healthcare visits over time.',
'Understanding appointment patterns helps healthcare providers optimize scheduling and service availability.',
ARRAY['appointments','visit scheduling','appointment trends']
),

(
'Patient Engagement',
'Patient engagement reflects how actively patients participate in healthcare services and interactions.',
'High levels of engagement often indicate stronger patient involvement in care processes.',
ARRAY['patient engagement','patient interaction','healthcare participation']
),

(
'Healthcare Activity Trends',
'Healthcare activity trends describe how healthcare interactions and service usage change across different time periods.',
'Trend analysis helps healthcare organizations anticipate demand and allocate resources effectively.',
ARRAY['healthcare trends','medical activity trends','service demand trends']
),

(
'Patient Participation',
'Patient participation reflects how widely healthcare services are utilized across the patient population.',
'Analyzing participation helps healthcare providers understand overall service reach.',
ARRAY['patient participation','service adoption','patient involvement']
),

(
'Clinical Activity Monitoring',
'Clinical activity monitoring focuses on observing patterns in healthcare delivery and patient interactions.',
'Monitoring clinical activity helps healthcare organizations maintain efficient service operations.',
ARRAY['clinical activity','medical operations','care monitoring']
),

(
'Patient Service Demand',
'Patient service demand reflects the level of need for healthcare services among patients.',
'Understanding demand helps healthcare providers plan staffing, services, and resources.',
ARRAY['service demand','healthcare demand','medical demand']
),

(
'Healthcare Interaction Distribution',
'Healthcare interaction distribution describes how patient interactions are spread across different services or providers.',
'Analyzing interaction distribution helps healthcare organizations understand how care is delivered.',
ARRAY['healthcare interactions','patient interactions','service distribution']
);

```