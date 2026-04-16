-- Domain schemas for Text2SQL: healthcare, retail, finance
-- Run this BEFORE generate_data.py

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
    state VARCHAR(10),
    insurance_type VARCHAR(50),
    registration_date DATE
);
COMMENT ON TABLE healthcare_schema.patients IS 'Stores patient demographic information including name, date of birth, location, and insurance details.';
COMMENT ON COLUMN healthcare_schema.patients.patient_id IS 'Unique system-generated identifier for each patient.';
COMMENT ON COLUMN healthcare_schema.patients.first_name IS 'First name of the patient.';
COMMENT ON COLUMN healthcare_schema.patients.last_name IS 'Last name of the patient.';
COMMENT ON COLUMN healthcare_schema.patients.date_of_birth IS 'Date of birth of the patient.';
COMMENT ON COLUMN healthcare_schema.patients.gender IS 'Gender of the patient (Male, Female, Other).';
COMMENT ON COLUMN healthcare_schema.patients.city IS 'City where the patient resides.';
COMMENT ON COLUMN healthcare_schema.patients.state IS 'State abbreviation where the patient resides.';
COMMENT ON COLUMN healthcare_schema.patients.insurance_type IS 'Type of health insurance (Medicare, Medicaid, Private, Employer, Uninsured).';
COMMENT ON COLUMN healthcare_schema.patients.registration_date IS 'Date when the patient was registered in the system.';

CREATE TABLE IF NOT EXISTS healthcare_schema.visits (
    visit_id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES healthcare_schema.patients(patient_id),
    admission_date DATE,
    discharge_date DATE,
    department VARCHAR(100),
    visit_type VARCHAR(50),
    total_cost NUMERIC(14,2)
);
COMMENT ON TABLE healthcare_schema.visits IS 'Records patient visits including admission, discharge, department, and cost information.';
COMMENT ON COLUMN healthcare_schema.visits.visit_id IS 'Unique system-generated identifier for each visit.';
COMMENT ON COLUMN healthcare_schema.visits.patient_id IS 'Foreign key referencing the patient who made the visit.';
COMMENT ON COLUMN healthcare_schema.visits.admission_date IS 'Date when the patient was admitted.';
COMMENT ON COLUMN healthcare_schema.visits.discharge_date IS 'Date when the patient was discharged.';
COMMENT ON COLUMN healthcare_schema.visits.department IS 'Hospital department where the visit occurred.';
COMMENT ON COLUMN healthcare_schema.visits.visit_type IS 'Type of visit (Inpatient, Outpatient, Emergency, Follow-up).';
COMMENT ON COLUMN healthcare_schema.visits.total_cost IS 'Total cost of the visit.';

CREATE TABLE IF NOT EXISTS healthcare_schema.diagnoses (
    diagnosis_id SERIAL PRIMARY KEY,
    visit_id INTEGER REFERENCES healthcare_schema.visits(visit_id),
    diagnosis_code VARCHAR(50),
    diagnosis_description TEXT,
    severity_level VARCHAR(20)
);
COMMENT ON TABLE healthcare_schema.diagnoses IS 'Stores diagnosis information linked to patient visits.';
COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_id IS 'Unique system-generated identifier for each diagnosis.';
COMMENT ON COLUMN healthcare_schema.diagnoses.visit_id IS 'Foreign key referencing the visit associated with this diagnosis.';
COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_code IS 'ICD-10 or similar diagnosis code.';
COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_description IS 'Human-readable description of the diagnosis.';
COMMENT ON COLUMN healthcare_schema.diagnoses.severity_level IS 'Severity level (Low, Medium, High, Critical).';

-- Business rules table for healthcare
CREATE TABLE IF NOT EXISTS healthcare_schema.healthcare_business_rules (
    rule_id SERIAL PRIMARY KEY,
    concept_name VARCHAR(150),
    description TEXT,
    insight TEXT,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE healthcare_schema.healthcare_business_rules IS 'Stores domain-level healthcare business knowledge used by the Intent Agent.';

-- ============================================================================
-- RETAIL SCHEMA
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS retail_schema;

CREATE TABLE IF NOT EXISTS retail_schema.customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(10),
    signup_date DATE
);
COMMENT ON TABLE retail_schema.customers IS 'Stores customer information including contact details and signup date.';
COMMENT ON COLUMN retail_schema.customers.customer_id IS 'Unique system-generated identifier for each customer.';
COMMENT ON COLUMN retail_schema.customers.first_name IS 'First name of the customer.';
COMMENT ON COLUMN retail_schema.customers.last_name IS 'Last name of the customer.';
COMMENT ON COLUMN retail_schema.customers.email IS 'Email address of the customer.';
COMMENT ON COLUMN retail_schema.customers.city IS 'City where the customer resides.';
COMMENT ON COLUMN retail_schema.customers.state IS 'State abbreviation where the customer resides.';
COMMENT ON COLUMN retail_schema.customers.signup_date IS 'Date when the customer signed up.';

CREATE TABLE IF NOT EXISTS retail_schema.products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(200),
    category VARCHAR(100),
    brand VARCHAR(100),
    price NUMERIC(10,2),
    launch_date DATE
);
COMMENT ON TABLE retail_schema.products IS 'Stores product catalog information including category, brand, and pricing.';
COMMENT ON COLUMN retail_schema.products.product_id IS 'Unique system-generated identifier for each product.';
COMMENT ON COLUMN retail_schema.products.product_name IS 'Name of the product.';
COMMENT ON COLUMN retail_schema.products.category IS 'Product category (Electronics, Clothing, Home, etc.).';
COMMENT ON COLUMN retail_schema.products.brand IS 'Brand name of the product.';
COMMENT ON COLUMN retail_schema.products.price IS 'Unit price of the product.';
COMMENT ON COLUMN retail_schema.products.launch_date IS 'Date when the product was launched.';

CREATE TABLE IF NOT EXISTS retail_schema.orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES retail_schema.customers(customer_id),
    product_id INTEGER REFERENCES retail_schema.products(product_id),
    order_date DATE,
    quantity INTEGER,
    total_amount NUMERIC(14,2)
);
COMMENT ON TABLE retail_schema.orders IS 'Records customer orders linking customers to products with quantities and amounts.';
COMMENT ON COLUMN retail_schema.orders.order_id IS 'Unique system-generated identifier for each order.';
COMMENT ON COLUMN retail_schema.orders.customer_id IS 'Foreign key referencing the customer who placed the order.';
COMMENT ON COLUMN retail_schema.orders.product_id IS 'Foreign key referencing the ordered product.';
COMMENT ON COLUMN retail_schema.orders.order_date IS 'Date when the order was placed.';
COMMENT ON COLUMN retail_schema.orders.quantity IS 'Number of units ordered.';
COMMENT ON COLUMN retail_schema.orders.total_amount IS 'Total amount for the order.';

-- Business rules table for retail
CREATE TABLE IF NOT EXISTS retail_schema.retail_business_rules (
    rule_id SERIAL PRIMARY KEY,
    concept_name VARCHAR(150),
    description TEXT,
    insight TEXT,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE retail_schema.retail_business_rules IS 'Stores domain-level retail business knowledge used by the Intent Agent.';

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
COMMENT ON TABLE finance_schema.accounts IS 'Stores customer bank account information including account type, branch location, and current balance.';
COMMENT ON COLUMN finance_schema.accounts.account_id IS 'Unique system-generated identifier assigned to each bank account.';
COMMENT ON COLUMN finance_schema.accounts.customer_name IS 'Full name of the customer who owns the bank account.';
COMMENT ON COLUMN finance_schema.accounts.account_type IS 'Type of bank account such as savings or checking.';
COMMENT ON COLUMN finance_schema.accounts.branch_city IS 'City where the bank branch managing the account is located.';
COMMENT ON COLUMN finance_schema.accounts.opening_date IS 'Date when the bank account was opened.';
COMMENT ON COLUMN finance_schema.accounts.current_balance IS 'Current available balance in the account.';

CREATE TABLE IF NOT EXISTS finance_schema.transactions (
    transaction_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES finance_schema.accounts(account_id),
    transaction_date DATE,
    transaction_type VARCHAR(50),
    amount NUMERIC(14,2),
    description VARCHAR(255)
);
COMMENT ON TABLE finance_schema.transactions IS 'Records financial transactions performed on customer accounts including debits and credits.';
COMMENT ON COLUMN finance_schema.transactions.transaction_id IS 'Unique system-generated identifier for each transaction.';
COMMENT ON COLUMN finance_schema.transactions.account_id IS 'Foreign key referencing the account on which the transaction occurred.';
COMMENT ON COLUMN finance_schema.transactions.transaction_date IS 'Date when the transaction was executed.';
COMMENT ON COLUMN finance_schema.transactions.transaction_type IS 'Type of transaction such as debit or credit.';
COMMENT ON COLUMN finance_schema.transactions.amount IS 'Monetary value of the transaction.';
COMMENT ON COLUMN finance_schema.transactions.description IS 'Short textual explanation describing the purpose of the transaction.';

CREATE TABLE IF NOT EXISTS finance_schema.loans (
    loan_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES finance_schema.accounts(account_id),
    loan_type VARCHAR(100),
    loan_amount NUMERIC(14,2),
    interest_rate NUMERIC(5,2),
    loan_start_date DATE,
    loan_end_date DATE
);
COMMENT ON TABLE finance_schema.loans IS 'Stores loan account information associated with customer accounts.';
COMMENT ON COLUMN finance_schema.loans.loan_id IS 'Unique system-generated identifier for each loan record.';
COMMENT ON COLUMN finance_schema.loans.account_id IS 'Foreign key referencing the account associated with the loan.';
COMMENT ON COLUMN finance_schema.loans.loan_type IS 'Category of loan such as home loan, auto loan, or personal loan.';
COMMENT ON COLUMN finance_schema.loans.loan_amount IS 'Total principal amount borrowed under the loan agreement.';
COMMENT ON COLUMN finance_schema.loans.interest_rate IS 'Annual interest rate applied to the loan expressed as a percentage.';
COMMENT ON COLUMN finance_schema.loans.loan_start_date IS 'Date when the loan repayment period began.';
COMMENT ON COLUMN finance_schema.loans.loan_end_date IS 'Date when the loan is scheduled to be fully repaid.';

-- Business rules table for finance
CREATE TABLE IF NOT EXISTS finance_schema.finance_business_rules (
    rule_id SERIAL PRIMARY KEY,
    concept_name VARCHAR(150),
    description TEXT,
    insight TEXT,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE finance_schema.finance_business_rules IS 'Stores domain-level financial business knowledge used by the Intent Agent.';

-- Schema comments
COMMENT ON SCHEMA healthcare_schema IS 'Healthcare domain: patients, visits, diagnoses';
COMMENT ON SCHEMA retail_schema IS 'Retail domain: customers, products, orders';
COMMENT ON SCHEMA finance_schema IS 'Finance domain: accounts, transactions, loans';
