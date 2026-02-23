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