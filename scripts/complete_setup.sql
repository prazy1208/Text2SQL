-- ============================================================================
-- COMPLETE TEXT2SQL DATABASE SETUP
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard → SQL Editor
-- ============================================================================

-- ============================================================================
-- HEALTHCARE SCHEMA
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS healthcare_schema;

CREATE TABLE IF NOT EXISTS healthcare_schema.patients (
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

CREATE TABLE IF NOT EXISTS healthcare_schema.visits (
    visit_id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES healthcare_schema.patients(patient_id),
    admission_date DATE,
    discharge_date DATE,
    department VARCHAR(100),
    visit_type VARCHAR(50),
    total_cost NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS healthcare_schema.diagnoses (
    diagnosis_id SERIAL PRIMARY KEY,
    visit_id INT REFERENCES healthcare_schema.visits(visit_id),
    diagnosis_code VARCHAR(20),
    diagnosis_description VARCHAR(255),
    severity_level VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS healthcare_schema.healthcare_business_rules (
    rule_id SERIAL PRIMARY KEY,
    concept_name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    insight TEXT,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Healthcare comments
COMMENT ON SCHEMA healthcare_schema IS 'Healthcare domain: patients, visits, diagnoses';
COMMENT ON TABLE healthcare_schema.patients IS 'Stores patient demographic information.';
COMMENT ON COLUMN healthcare_schema.patients.patient_id IS 'Unique identifier for each patient.';
COMMENT ON COLUMN healthcare_schema.patients.first_name IS 'Patient first name.';
COMMENT ON COLUMN healthcare_schema.patients.last_name IS 'Patient last name.';
COMMENT ON COLUMN healthcare_schema.patients.date_of_birth IS 'Date of birth.';
COMMENT ON COLUMN healthcare_schema.patients.gender IS 'Gender (Male, Female, Other).';
COMMENT ON COLUMN healthcare_schema.patients.city IS 'City of residence.';
COMMENT ON COLUMN healthcare_schema.patients.state IS 'State of residence.';
COMMENT ON COLUMN healthcare_schema.patients.insurance_type IS 'Insurance type (Medicare, Medicaid, Private, etc.).';
COMMENT ON COLUMN healthcare_schema.patients.registration_date IS 'Registration date.';

COMMENT ON TABLE healthcare_schema.visits IS 'Records patient visits.';
COMMENT ON COLUMN healthcare_schema.visits.visit_id IS 'Unique identifier for each visit.';
COMMENT ON COLUMN healthcare_schema.visits.patient_id IS 'Foreign key to patients.';
COMMENT ON COLUMN healthcare_schema.visits.admission_date IS 'Admission date.';
COMMENT ON COLUMN healthcare_schema.visits.discharge_date IS 'Discharge date.';
COMMENT ON COLUMN healthcare_schema.visits.department IS 'Hospital department.';
COMMENT ON COLUMN healthcare_schema.visits.visit_type IS 'Visit type (Inpatient, Outpatient, Emergency).';
COMMENT ON COLUMN healthcare_schema.visits.total_cost IS 'Total visit cost.';

COMMENT ON TABLE healthcare_schema.diagnoses IS 'Stores diagnosis information.';
COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_id IS 'Unique identifier for each diagnosis.';
COMMENT ON COLUMN healthcare_schema.diagnoses.visit_id IS 'Foreign key to visits.';
COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_code IS 'ICD diagnosis code.';
COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_description IS 'Diagnosis description.';
COMMENT ON COLUMN healthcare_schema.diagnoses.severity_level IS 'Severity (Low, Medium, High, Critical).';

-- ============================================================================
-- RETAIL SCHEMA
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS retail_schema;

CREATE TABLE IF NOT EXISTS retail_schema.customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(150),
    city VARCHAR(100),
    state VARCHAR(100),
    signup_date DATE
);

CREATE TABLE IF NOT EXISTS retail_schema.products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(150),
    category VARCHAR(100),
    brand VARCHAR(100),
    price NUMERIC(10,2),
    launch_date DATE
);

CREATE TABLE IF NOT EXISTS retail_schema.orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES retail_schema.customers(customer_id),
    product_id INT REFERENCES retail_schema.products(product_id),
    order_date DATE,
    quantity INT,
    total_amount NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS retail_schema.retail_business_rules (
    rule_id SERIAL PRIMARY KEY,
    concept_name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    insight TEXT,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Retail comments
COMMENT ON SCHEMA retail_schema IS 'Retail domain: customers, products, orders';
COMMENT ON TABLE retail_schema.customers IS 'Stores customer information.';
COMMENT ON COLUMN retail_schema.customers.customer_id IS 'Unique identifier for each customer.';
COMMENT ON COLUMN retail_schema.customers.first_name IS 'Customer first name.';
COMMENT ON COLUMN retail_schema.customers.last_name IS 'Customer last name.';
COMMENT ON COLUMN retail_schema.customers.email IS 'Customer email.';
COMMENT ON COLUMN retail_schema.customers.city IS 'City of residence.';
COMMENT ON COLUMN retail_schema.customers.state IS 'State of residence.';
COMMENT ON COLUMN retail_schema.customers.signup_date IS 'Signup date.';

COMMENT ON TABLE retail_schema.products IS 'Stores product catalog.';
COMMENT ON COLUMN retail_schema.products.product_id IS 'Unique identifier for each product.';
COMMENT ON COLUMN retail_schema.products.product_name IS 'Product name.';
COMMENT ON COLUMN retail_schema.products.category IS 'Product category.';
COMMENT ON COLUMN retail_schema.products.brand IS 'Product brand.';
COMMENT ON COLUMN retail_schema.products.price IS 'Product price.';
COMMENT ON COLUMN retail_schema.products.launch_date IS 'Launch date.';

COMMENT ON TABLE retail_schema.orders IS 'Records customer orders.';
COMMENT ON COLUMN retail_schema.orders.order_id IS 'Unique identifier for each order.';
COMMENT ON COLUMN retail_schema.orders.customer_id IS 'Foreign key to customers.';
COMMENT ON COLUMN retail_schema.orders.product_id IS 'Foreign key to products.';
COMMENT ON COLUMN retail_schema.orders.order_date IS 'Order date.';
COMMENT ON COLUMN retail_schema.orders.quantity IS 'Quantity ordered.';
COMMENT ON COLUMN retail_schema.orders.total_amount IS 'Total order amount.';

-- ============================================================================
-- FINANCE SCHEMA
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS finance_schema;

CREATE TABLE IF NOT EXISTS finance_schema.accounts (
    account_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(150),
    account_type VARCHAR(50),
    branch_city VARCHAR(100),
    opening_date DATE,
    current_balance NUMERIC(14,2)
);

CREATE TABLE IF NOT EXISTS finance_schema.transactions (
    transaction_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES finance_schema.accounts(account_id),
    transaction_date DATE,
    transaction_type VARCHAR(50),
    amount NUMERIC(14,2),
    description VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS finance_schema.loans (
    loan_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES finance_schema.accounts(account_id),
    loan_type VARCHAR(100),
    loan_amount NUMERIC(14,2),
    interest_rate NUMERIC(5,2),
    loan_start_date DATE,
    loan_end_date DATE
);

CREATE TABLE IF NOT EXISTS finance_schema.finance_business_rules (
    rule_id SERIAL PRIMARY KEY,
    concept_name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    insight TEXT,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Finance comments
COMMENT ON SCHEMA finance_schema IS 'Finance domain: accounts, transactions, loans';
COMMENT ON TABLE finance_schema.accounts IS 'Stores bank account information.';
COMMENT ON COLUMN finance_schema.accounts.account_id IS 'Unique identifier for each account.';
COMMENT ON COLUMN finance_schema.accounts.customer_name IS 'Customer name.';
COMMENT ON COLUMN finance_schema.accounts.account_type IS 'Account type (savings, checking).';
COMMENT ON COLUMN finance_schema.accounts.branch_city IS 'Branch city.';
COMMENT ON COLUMN finance_schema.accounts.opening_date IS 'Account opening date.';
COMMENT ON COLUMN finance_schema.accounts.current_balance IS 'Current balance.';

COMMENT ON TABLE finance_schema.transactions IS 'Records financial transactions.';
COMMENT ON COLUMN finance_schema.transactions.transaction_id IS 'Unique identifier for each transaction.';
COMMENT ON COLUMN finance_schema.transactions.account_id IS 'Foreign key to accounts.';
COMMENT ON COLUMN finance_schema.transactions.transaction_date IS 'Transaction date.';
COMMENT ON COLUMN finance_schema.transactions.transaction_type IS 'Transaction type (debit, credit).';
COMMENT ON COLUMN finance_schema.transactions.amount IS 'Transaction amount.';
COMMENT ON COLUMN finance_schema.transactions.description IS 'Transaction description.';

COMMENT ON TABLE finance_schema.loans IS 'Stores loan information.';
COMMENT ON COLUMN finance_schema.loans.loan_id IS 'Unique identifier for each loan.';
COMMENT ON COLUMN finance_schema.loans.account_id IS 'Foreign key to accounts.';
COMMENT ON COLUMN finance_schema.loans.loan_type IS 'Loan type (home, auto, personal).';
COMMENT ON COLUMN finance_schema.loans.loan_amount IS 'Loan principal amount.';
COMMENT ON COLUMN finance_schema.loans.interest_rate IS 'Annual interest rate.';
COMMENT ON COLUMN finance_schema.loans.loan_start_date IS 'Loan start date.';
COMMENT ON COLUMN finance_schema.loans.loan_end_date IS 'Loan end date.';

-- ============================================================================
-- APP SCHEMA (sessions, agent outputs)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS app_schema;

CREATE TABLE IF NOT EXISTS app_schema.sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_schema.intent_agent_output (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES app_schema.sessions(session_id) ON DELETE CASCADE,
    use_case VARCHAR(64) NOT NULL,
    user_input TEXT NOT NULL,
    rephrased_question TEXT,
    keywords TEXT[],
    business_insights TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_intent_agent_output_session_id ON app_schema.intent_agent_output(session_id);
CREATE INDEX IF NOT EXISTS idx_intent_agent_output_use_case ON app_schema.intent_agent_output(use_case);

CREATE TABLE IF NOT EXISTS app_schema.table_agent_output (
    id SERIAL PRIMARY KEY,
    intent_output_id INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    selected_tables TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

CREATE TABLE IF NOT EXISTS app_schema.column_agent_output (
    id SERIAL PRIMARY KEY,
    table_agent_output_id INT NOT NULL REFERENCES app_schema.table_agent_output(id) ON DELETE CASCADE,
    selected_columns JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (table_agent_output_id)
);

COMMENT ON SCHEMA app_schema IS 'Application/session data for Text2SQL';
COMMENT ON TABLE app_schema.sessions IS 'One row per chat session';
COMMENT ON TABLE app_schema.intent_agent_output IS 'Intent Agent output per query';
COMMENT ON TABLE app_schema.table_agent_output IS 'Table Agent: selected tables';
COMMENT ON TABLE app_schema.column_agent_output IS 'Column Agent: selected columns';

-- ============================================================================
-- DONE - Schemas and tables created!
-- ============================================================================
