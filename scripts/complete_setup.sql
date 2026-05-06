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
    department_id INT,
    visit_type VARCHAR(50),
    total_cost NUMERIC(12,2)
);
ALTER TABLE healthcare_schema.visits
    ADD COLUMN IF NOT EXISTS department_id INT;


CREATE TABLE IF NOT EXISTS healthcare_schema.diagnoses (
    diagnosis_id SERIAL PRIMARY KEY,
    visit_id INT REFERENCES healthcare_schema.visits(visit_id),
    diagnosis_code VARCHAR(20),
    diagnosis_description VARCHAR(255),
    severity_level VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS healthcare_schema.departments (
    department_id SERIAL PRIMARY KEY,
    department_name VARCHAR(100),
    location VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS healthcare_schema.providers (
    provider_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    specialty VARCHAR(100),
    department_id INT REFERENCES healthcare_schema.departments(department_id),
    years_of_experience INT
);

CREATE TABLE IF NOT EXISTS healthcare_schema.procedures (
    procedure_id SERIAL PRIMARY KEY,
    visit_id INT REFERENCES healthcare_schema.visits(visit_id),
    provider_id INT REFERENCES healthcare_schema.providers(provider_id),
    procedure_name VARCHAR(100),
    procedure_date DATE,
    cost DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS healthcare_schema.medications (
    medication_id SERIAL PRIMARY KEY,
    medication_name VARCHAR(100),
    manufacturer VARCHAR(100),
    unit_cost DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS healthcare_schema.prescriptions (
    prescription_id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES healthcare_schema.patients(patient_id),
    medication_id INT REFERENCES healthcare_schema.medications(medication_id),
    provider_id INT REFERENCES healthcare_schema.providers(provider_id),
    dosage VARCHAR(50),
    start_date DATE,
    end_date DATE
);

CREATE TABLE IF NOT EXISTS healthcare_schema.billing (
    billing_id SERIAL PRIMARY KEY,
    visit_id INT REFERENCES healthcare_schema.visits(visit_id),
    total_amount DECIMAL(12,2),
    insurance_covered_amount DECIMAL(12,2),
    out_of_pocket_amount DECIMAL(12,2),
    billing_date DATE
);

CREATE TABLE IF NOT EXISTS healthcare_schema.insurance_claims (
    claim_id SERIAL PRIMARY KEY,
    visit_id INT REFERENCES healthcare_schema.visits(visit_id),
    patient_id INT REFERENCES healthcare_schema.patients(patient_id),
    claim_status VARCHAR(50),
    claim_amount DECIMAL(12,2),
    approved_amount DECIMAL(12,2),
    claim_date DATE
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
COMMENT ON COLUMN healthcare_schema.visits.department IS 'Legacy text department name (kept for backward compatibility).';
COMMENT ON COLUMN healthcare_schema.visits.department_id IS 'Foreign key to departments master table.';
COMMENT ON COLUMN healthcare_schema.visits.visit_type IS 'Visit type (Inpatient, Outpatient, Emergency).';
COMMENT ON COLUMN healthcare_schema.visits.total_cost IS 'Total visit cost.';

COMMENT ON TABLE healthcare_schema.diagnoses IS 'Stores diagnosis information.';
COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_id IS 'Unique identifier for each diagnosis.';
COMMENT ON COLUMN healthcare_schema.diagnoses.visit_id IS 'Foreign key to visits.';
COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_code IS 'ICD diagnosis code.';
COMMENT ON COLUMN healthcare_schema.diagnoses.diagnosis_description IS 'Diagnosis description.';
COMMENT ON COLUMN healthcare_schema.diagnoses.severity_level IS 'Severity (Low, Medium, High, Critical).';

COMMENT ON TABLE healthcare_schema.departments IS 'Hospital departments such as Cardiology, Emergency, etc.';
COMMENT ON COLUMN healthcare_schema.departments.department_id IS 'Unique identifier for each department';
COMMENT ON COLUMN healthcare_schema.departments.department_name IS 'Name of the department';
COMMENT ON COLUMN healthcare_schema.departments.location IS 'Physical location within hospital';

COMMENT ON TABLE healthcare_schema.providers IS 'Healthcare professionals including doctors and nurses';
COMMENT ON COLUMN healthcare_schema.providers.provider_id IS 'Unique identifier for provider';
COMMENT ON COLUMN healthcare_schema.providers.first_name IS 'Provider first name';
COMMENT ON COLUMN healthcare_schema.providers.last_name IS 'Provider last name';
COMMENT ON COLUMN healthcare_schema.providers.specialty IS 'Medical specialization';
COMMENT ON COLUMN healthcare_schema.providers.department_id IS 'Department provider belongs to';
COMMENT ON COLUMN healthcare_schema.providers.years_of_experience IS 'Years of professional experience';

COMMENT ON TABLE healthcare_schema.procedures IS 'Medical procedures performed during patient visits';
COMMENT ON COLUMN healthcare_schema.procedures.procedure_id IS 'Unique procedure identifier';
COMMENT ON COLUMN healthcare_schema.procedures.visit_id IS 'Associated visit';
COMMENT ON COLUMN healthcare_schema.procedures.provider_id IS 'Provider performing procedure';
COMMENT ON COLUMN healthcare_schema.procedures.procedure_name IS 'Name of procedure';
COMMENT ON COLUMN healthcare_schema.procedures.procedure_date IS 'Date performed';
COMMENT ON COLUMN healthcare_schema.procedures.cost IS 'Cost of procedure';

COMMENT ON TABLE healthcare_schema.medications IS 'Master list of medications';
COMMENT ON COLUMN healthcare_schema.medications.medication_id IS 'Unique medication identifier';
COMMENT ON COLUMN healthcare_schema.medications.medication_name IS 'Name of medication';
COMMENT ON COLUMN healthcare_schema.medications.manufacturer IS 'Manufacturer name';
COMMENT ON COLUMN healthcare_schema.medications.unit_cost IS 'Cost per unit';

COMMENT ON TABLE healthcare_schema.prescriptions IS 'Prescribed medications for patients';
COMMENT ON COLUMN healthcare_schema.prescriptions.prescription_id IS 'Unique prescription identifier';
COMMENT ON COLUMN healthcare_schema.prescriptions.patient_id IS 'Patient receiving medication';
COMMENT ON COLUMN healthcare_schema.prescriptions.medication_id IS 'Medication prescribed';
COMMENT ON COLUMN healthcare_schema.prescriptions.provider_id IS 'Provider prescribing medication';
COMMENT ON COLUMN healthcare_schema.prescriptions.dosage IS 'Dosage instructions';
COMMENT ON COLUMN healthcare_schema.prescriptions.start_date IS 'Prescription start date';
COMMENT ON COLUMN healthcare_schema.prescriptions.end_date IS 'Prescription end date';

COMMENT ON TABLE healthcare_schema.billing IS 'Billing details for each visit';
COMMENT ON COLUMN healthcare_schema.billing.billing_id IS 'Unique billing identifier';
COMMENT ON COLUMN healthcare_schema.billing.visit_id IS 'Visit being billed';
COMMENT ON COLUMN healthcare_schema.billing.total_amount IS 'Total billed amount';
COMMENT ON COLUMN healthcare_schema.billing.insurance_covered_amount IS 'Amount covered by insurance';
COMMENT ON COLUMN healthcare_schema.billing.out_of_pocket_amount IS 'Amount paid by patient';
COMMENT ON COLUMN healthcare_schema.billing.billing_date IS 'Billing date';

COMMENT ON TABLE healthcare_schema.insurance_claims IS 'Insurance claim processing details';
COMMENT ON COLUMN healthcare_schema.insurance_claims.claim_id IS 'Unique claim identifier';
COMMENT ON COLUMN healthcare_schema.insurance_claims.visit_id IS 'Associated visit';
COMMENT ON COLUMN healthcare_schema.insurance_claims.patient_id IS 'Patient filing claim';
COMMENT ON COLUMN healthcare_schema.insurance_claims.claim_status IS 'Status (Pending, Approved, Rejected)';
COMMENT ON COLUMN healthcare_schema.insurance_claims.claim_amount IS 'Requested claim amount';
COMMENT ON COLUMN healthcare_schema.insurance_claims.approved_amount IS 'Approved amount';
COMMENT ON COLUMN healthcare_schema.insurance_claims.claim_date IS 'Date of claim submission';

ALTER TABLE healthcare_schema.visits
    ADD COLUMN IF NOT EXISTS department_id INT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_visits_department_id'
          AND connamespace = 'healthcare_schema'::regnamespace
    ) THEN
        ALTER TABLE healthcare_schema.visits
            ADD CONSTRAINT fk_visits_department_id
            FOREIGN KEY (department_id)
            REFERENCES healthcare_schema.departments(department_id);
    END IF;
END $$;

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
    category_id INT,
    brand VARCHAR(100),
    price NUMERIC(10,2),
    launch_date DATE
);
ALTER TABLE retail_schema.products
    ADD COLUMN IF NOT EXISTS category_id INT;


CREATE TABLE IF NOT EXISTS retail_schema.orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES retail_schema.customers(customer_id),
    product_id INT REFERENCES retail_schema.products(product_id),
    order_date DATE,
    quantity INT,
    total_amount NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS retail_schema.categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100),
    parent_category_id INT REFERENCES retail_schema.categories(category_id)
);

CREATE TABLE IF NOT EXISTS retail_schema.suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(100),
    contact_email VARCHAR(100),
    phone VARCHAR(20),
    city VARCHAR(50),
    state VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS retail_schema.stores (
    store_id SERIAL PRIMARY KEY,
    store_name VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    store_type VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS retail_schema.inventory (
    inventory_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES retail_schema.products(product_id),
    store_id INT REFERENCES retail_schema.stores(store_id),
    stock_quantity INT,
    last_updated TIMESTAMP
);

CREATE TABLE IF NOT EXISTS retail_schema.shipments (
    shipment_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES retail_schema.orders(order_id),
    shipment_date DATE,
    delivery_date DATE,
    shipment_status VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS retail_schema.reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES retail_schema.products(product_id),
    customer_id INT REFERENCES retail_schema.customers(customer_id),
    rating INT,
    review_text TEXT,
    review_date DATE
);

CREATE TABLE IF NOT EXISTS retail_schema.promotions (
    promotion_id SERIAL PRIMARY KEY,
    promotion_name VARCHAR(100),
    discount_percentage DECIMAL(5,2),
    start_date DATE,
    end_date DATE
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
COMMENT ON COLUMN retail_schema.products.category IS 'Legacy text category (kept for backward compatibility).';
COMMENT ON COLUMN retail_schema.products.category_id IS 'Foreign key to categories hierarchy.';
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

COMMENT ON TABLE retail_schema.categories IS 'Product category hierarchy';
COMMENT ON COLUMN retail_schema.categories.category_id IS 'Unique category identifier';
COMMENT ON COLUMN retail_schema.categories.category_name IS 'Category name';
COMMENT ON COLUMN retail_schema.categories.parent_category_id IS 'Parent category for hierarchical grouping';

COMMENT ON TABLE retail_schema.suppliers IS 'Suppliers providing products';
COMMENT ON COLUMN retail_schema.suppliers.supplier_id IS 'Unique supplier identifier';
COMMENT ON COLUMN retail_schema.suppliers.supplier_name IS 'Supplier name';
COMMENT ON COLUMN retail_schema.suppliers.contact_email IS 'Supplier contact email';
COMMENT ON COLUMN retail_schema.suppliers.phone IS 'Supplier phone number';
COMMENT ON COLUMN retail_schema.suppliers.city IS 'Supplier city';
COMMENT ON COLUMN retail_schema.suppliers.state IS 'Supplier state';

COMMENT ON TABLE retail_schema.stores IS 'Retail store locations';
COMMENT ON COLUMN retail_schema.stores.store_id IS 'Unique store identifier';
COMMENT ON COLUMN retail_schema.stores.store_name IS 'Store name';
COMMENT ON COLUMN retail_schema.stores.city IS 'Store city';
COMMENT ON COLUMN retail_schema.stores.state IS 'Store state';
COMMENT ON COLUMN retail_schema.stores.store_type IS 'Type (online/physical)';

COMMENT ON TABLE retail_schema.inventory IS 'Inventory levels per product and store';
COMMENT ON COLUMN retail_schema.inventory.inventory_id IS 'Unique inventory record';
COMMENT ON COLUMN retail_schema.inventory.product_id IS 'Product being tracked';
COMMENT ON COLUMN retail_schema.inventory.store_id IS 'Store holding inventory';
COMMENT ON COLUMN retail_schema.inventory.stock_quantity IS 'Available stock quantity';
COMMENT ON COLUMN retail_schema.inventory.last_updated IS 'Last update timestamp';

COMMENT ON TABLE retail_schema.shipments IS 'Tracks shipment and delivery of orders';
COMMENT ON COLUMN retail_schema.shipments.shipment_id IS 'Unique shipment identifier';
COMMENT ON COLUMN retail_schema.shipments.order_id IS 'Order being shipped';
COMMENT ON COLUMN retail_schema.shipments.shipment_date IS 'Date shipped';
COMMENT ON COLUMN retail_schema.shipments.delivery_date IS 'Date delivered';
COMMENT ON COLUMN retail_schema.shipments.shipment_status IS 'Delivery status';

COMMENT ON TABLE retail_schema.reviews IS 'Customer reviews and ratings for products';
COMMENT ON COLUMN retail_schema.reviews.review_id IS 'Unique review identifier';
COMMENT ON COLUMN retail_schema.reviews.product_id IS 'Reviewed product';
COMMENT ON COLUMN retail_schema.reviews.customer_id IS 'Customer writing review';
COMMENT ON COLUMN retail_schema.reviews.rating IS 'Rating score (1-5)';
COMMENT ON COLUMN retail_schema.reviews.review_text IS 'Written feedback';
COMMENT ON COLUMN retail_schema.reviews.review_date IS 'Date of review';

COMMENT ON TABLE retail_schema.promotions IS 'Marketing promotions and discounts';
COMMENT ON COLUMN retail_schema.promotions.promotion_id IS 'Unique promotion identifier';
COMMENT ON COLUMN retail_schema.promotions.promotion_name IS 'Promotion campaign name';
COMMENT ON COLUMN retail_schema.promotions.discount_percentage IS 'Discount percentage applied';
COMMENT ON COLUMN retail_schema.promotions.start_date IS 'Promotion start date';
COMMENT ON COLUMN retail_schema.promotions.end_date IS 'Promotion end date';

ALTER TABLE retail_schema.products
    ADD COLUMN IF NOT EXISTS category_id INT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_products_category_id'
          AND connamespace = 'retail_schema'::regnamespace
    ) THEN
        ALTER TABLE retail_schema.products
            ADD CONSTRAINT fk_products_category_id
            FOREIGN KEY (category_id)
            REFERENCES retail_schema.categories(category_id);
    END IF;
END $$;

-- ============================================================================
-- FINANCE SCHEMA
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS finance_schema;

CREATE TABLE IF NOT EXISTS finance_schema.accounts (
    account_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(150),
    customer_id INT,
    account_type VARCHAR(50),
    branch_city VARCHAR(100),
    branch_id INT,
    opening_date DATE,
    current_balance NUMERIC(14,2)
);
ALTER TABLE finance_schema.accounts
    ADD COLUMN IF NOT EXISTS customer_id INT;
ALTER TABLE finance_schema.accounts
    ADD COLUMN IF NOT EXISTS branch_id INT;


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

CREATE TABLE IF NOT EXISTS finance_schema.customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    city VARCHAR(50),
    state VARCHAR(50),
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finance_schema.branches (
    branch_id SERIAL PRIMARY KEY,
    branch_name VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS finance_schema.credit_cards (
    card_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES finance_schema.customers(customer_id),
    card_type VARCHAR(50),
    credit_limit DECIMAL(12,2),
    current_balance DECIMAL(12,2),
    issue_date DATE,
    expiry_date DATE
);

CREATE TABLE IF NOT EXISTS finance_schema.payments (
    payment_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES finance_schema.accounts(account_id),
    loan_id INT REFERENCES finance_schema.loans(loan_id),
    payment_amount DECIMAL(12,2),
    payment_date DATE,
    payment_type VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS finance_schema.investment_accounts (
    investment_account_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES finance_schema.customers(customer_id),
    account_type VARCHAR(50),
    total_value DECIMAL(14,2),
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finance_schema.account_balances_history (
    record_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES finance_schema.accounts(account_id),
    balance DECIMAL(12,2),
    recorded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finance_schema.fraud_alerts (
    alert_id SERIAL PRIMARY KEY,
    transaction_id INT REFERENCES finance_schema.transactions(transaction_id),
    alert_type VARCHAR(50),
    alert_status VARCHAR(50),
    created_at TIMESTAMP
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
COMMENT ON COLUMN finance_schema.accounts.customer_name IS 'Legacy customer name text (kept for backward compatibility).';
COMMENT ON COLUMN finance_schema.accounts.customer_id IS 'Foreign key to finance customers master.';
COMMENT ON COLUMN finance_schema.accounts.account_type IS 'Account type (savings, checking).';
COMMENT ON COLUMN finance_schema.accounts.branch_city IS 'Legacy branch city text (kept for backward compatibility).';
COMMENT ON COLUMN finance_schema.accounts.branch_id IS 'Foreign key to branch master.';
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

COMMENT ON TABLE finance_schema.customers IS 'Customer master data storing personal and contact details';
COMMENT ON COLUMN finance_schema.customers.customer_id IS 'Unique identifier for each customer';
COMMENT ON COLUMN finance_schema.customers.first_name IS 'Customer first name';
COMMENT ON COLUMN finance_schema.customers.last_name IS 'Customer last name';
COMMENT ON COLUMN finance_schema.customers.email IS 'Customer email address';
COMMENT ON COLUMN finance_schema.customers.phone IS 'Customer phone number';
COMMENT ON COLUMN finance_schema.customers.city IS 'City where customer resides';
COMMENT ON COLUMN finance_schema.customers.state IS 'State where customer resides';
COMMENT ON COLUMN finance_schema.customers.created_at IS 'Timestamp when customer profile was created';

COMMENT ON TABLE finance_schema.branches IS 'Bank branch information';
COMMENT ON COLUMN finance_schema.branches.branch_id IS 'Unique identifier for branch';
COMMENT ON COLUMN finance_schema.branches.branch_name IS 'Name of the branch';
COMMENT ON COLUMN finance_schema.branches.city IS 'City where branch is located';
COMMENT ON COLUMN finance_schema.branches.state IS 'State where branch is located';

COMMENT ON TABLE finance_schema.credit_cards IS 'Credit card accounts issued to customers';
COMMENT ON COLUMN finance_schema.credit_cards.card_id IS 'Unique credit card identifier';
COMMENT ON COLUMN finance_schema.credit_cards.customer_id IS 'Customer owning the card';
COMMENT ON COLUMN finance_schema.credit_cards.card_type IS 'Type of card (e.g., Visa, Mastercard)';
COMMENT ON COLUMN finance_schema.credit_cards.credit_limit IS 'Maximum allowed spending limit';
COMMENT ON COLUMN finance_schema.credit_cards.current_balance IS 'Outstanding balance on the card';
COMMENT ON COLUMN finance_schema.credit_cards.issue_date IS 'Date when card was issued';
COMMENT ON COLUMN finance_schema.credit_cards.expiry_date IS 'Card expiration date';

COMMENT ON TABLE finance_schema.payments IS 'Payments made towards loans or accounts';
COMMENT ON COLUMN finance_schema.payments.payment_id IS 'Unique payment identifier';
COMMENT ON COLUMN finance_schema.payments.account_id IS 'Account from which payment was made';
COMMENT ON COLUMN finance_schema.payments.loan_id IS 'Loan associated with payment (if applicable)';
COMMENT ON COLUMN finance_schema.payments.payment_amount IS 'Amount paid';
COMMENT ON COLUMN finance_schema.payments.payment_date IS 'Date of payment';
COMMENT ON COLUMN finance_schema.payments.payment_type IS 'Type of payment (EMI, credit card, etc.)';

COMMENT ON TABLE finance_schema.investment_accounts IS 'Investment portfolios held by customers';
COMMENT ON COLUMN finance_schema.investment_accounts.investment_account_id IS 'Unique investment account identifier';
COMMENT ON COLUMN finance_schema.investment_accounts.customer_id IS 'Customer owning investment account';
COMMENT ON COLUMN finance_schema.investment_accounts.account_type IS 'Type of investment (stocks, mutual funds)';
COMMENT ON COLUMN finance_schema.investment_accounts.total_value IS 'Total portfolio value';
COMMENT ON COLUMN finance_schema.investment_accounts.created_at IS 'Account creation timestamp';

COMMENT ON TABLE finance_schema.account_balances_history IS 'Historical record of account balances';
COMMENT ON COLUMN finance_schema.account_balances_history.record_id IS 'Unique record identifier';
COMMENT ON COLUMN finance_schema.account_balances_history.account_id IS 'Account being tracked';
COMMENT ON COLUMN finance_schema.account_balances_history.balance IS 'Balance at given timestamp';
COMMENT ON COLUMN finance_schema.account_balances_history.recorded_at IS 'Timestamp of recorded balance';

COMMENT ON TABLE finance_schema.fraud_alerts IS 'Flags suspicious or fraudulent transactions';
COMMENT ON COLUMN finance_schema.fraud_alerts.alert_id IS 'Unique alert identifier';
COMMENT ON COLUMN finance_schema.fraud_alerts.transaction_id IS 'Transaction flagged for fraud';
COMMENT ON COLUMN finance_schema.fraud_alerts.alert_type IS 'Type of fraud detected';
COMMENT ON COLUMN finance_schema.fraud_alerts.alert_status IS 'Status of investigation';
COMMENT ON COLUMN finance_schema.fraud_alerts.created_at IS 'Timestamp when alert was generated';

ALTER TABLE finance_schema.accounts
    ADD COLUMN IF NOT EXISTS customer_id INT;
ALTER TABLE finance_schema.accounts
    ADD COLUMN IF NOT EXISTS branch_id INT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_accounts_customer_id'
          AND connamespace = 'finance_schema'::regnamespace
    ) THEN
        ALTER TABLE finance_schema.accounts
            ADD CONSTRAINT fk_accounts_customer_id
            FOREIGN KEY (customer_id)
            REFERENCES finance_schema.customers(customer_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_accounts_branch_id'
          AND connamespace = 'finance_schema'::regnamespace
    ) THEN
        ALTER TABLE finance_schema.accounts
            ADD CONSTRAINT fk_accounts_branch_id
            FOREIGN KEY (branch_id)
            REFERENCES finance_schema.branches(branch_id);
    END IF;
END $$;

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

CREATE TABLE IF NOT EXISTS app_schema.few_shot_agent_output (
    id SERIAL PRIMARY KEY,
    intent_output_id INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    few_shot_examples JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

CREATE TABLE IF NOT EXISTS app_schema.gen_sql_agent_output (
    id SERIAL PRIMARY KEY,
    intent_output_id INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    generated_sql TEXT NOT NULL DEFAULT '',
    reasoning_summary TEXT,
    validation_passed BOOLEAN NOT NULL DEFAULT FALSE,
    validation_error_codes TEXT NOT NULL DEFAULT '',
    validation_error_message TEXT NOT NULL DEFAULT '',
    blocked_keywords TEXT NOT NULL DEFAULT '',
    is_single_statement BOOLEAN NOT NULL DEFAULT FALSE,
    is_select_only BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

COMMENT ON SCHEMA app_schema IS 'Application/session data for Text2SQL';
COMMENT ON TABLE app_schema.sessions IS 'One row per chat session';
COMMENT ON TABLE app_schema.intent_agent_output IS 'Intent Agent output per query';
COMMENT ON TABLE app_schema.table_agent_output IS 'Table Agent: selected tables';
COMMENT ON TABLE app_schema.column_agent_output IS 'Column Agent: selected columns';
COMMENT ON TABLE app_schema.few_shot_agent_output IS 'Few-Shot Agent: selected few_shot_examples';
COMMENT ON TABLE app_schema.gen_sql_agent_output IS 'Gen-SQL Agent: generated SQL and validation';

-- ============================================================================
-- DOMAIN FK METADATA (table_relationships) — required for Table / Column / Gen-SQL agents
-- Same DDL as scripts/create_domain_schema_table_relationships.sql
-- Populate rows with: python scripts/extract_and_load_relationships.py
-- ============================================================================

CREATE TABLE IF NOT EXISTS healthcare_schema.table_relationships (
    id                  SERIAL PRIMARY KEY,
    source_table        TEXT NOT NULL,
    source_column       TEXT NOT NULL,
    target_schema       TEXT NOT NULL,
    target_table        TEXT NOT NULL,
    target_column       TEXT NOT NULL,
    relationship_text   TEXT NOT NULL,
    constraint_name     VARCHAR(256),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_healthcare_table_relationships_edge
        UNIQUE (source_table, source_column, target_schema, target_table, target_column)
);

CREATE INDEX IF NOT EXISTS idx_healthcare_table_relationships_source
    ON healthcare_schema.table_relationships (source_table);
CREATE INDEX IF NOT EXISTS idx_healthcare_table_relationships_source_col
    ON healthcare_schema.table_relationships (source_table, source_column);

COMMENT ON TABLE healthcare_schema.table_relationships IS 'Foreign keys with referencing tables in healthcare_schema; target_schema for referenced side';
COMMENT ON COLUMN healthcare_schema.table_relationships.target_schema IS 'Schema of the referenced (target) table';
COMMENT ON COLUMN healthcare_schema.table_relationships.relationship_text IS 'Canonical line for LLM context';

CREATE TABLE IF NOT EXISTS retail_schema.table_relationships (
    id                  SERIAL PRIMARY KEY,
    source_table        TEXT NOT NULL,
    source_column       TEXT NOT NULL,
    target_schema       TEXT NOT NULL,
    target_table        TEXT NOT NULL,
    target_column       TEXT NOT NULL,
    relationship_text   TEXT NOT NULL,
    constraint_name     VARCHAR(256),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_retail_table_relationships_edge
        UNIQUE (source_table, source_column, target_schema, target_table, target_column)
);

CREATE INDEX IF NOT EXISTS idx_retail_table_relationships_source
    ON retail_schema.table_relationships (source_table);
CREATE INDEX IF NOT EXISTS idx_retail_table_relationships_source_col
    ON retail_schema.table_relationships (source_table, source_column);

COMMENT ON TABLE retail_schema.table_relationships IS 'Foreign keys with referencing tables in retail_schema; target_schema for referenced side';
COMMENT ON COLUMN retail_schema.table_relationships.target_schema IS 'Schema of the referenced (target) table';
COMMENT ON COLUMN retail_schema.table_relationships.relationship_text IS 'Canonical line for LLM context';

CREATE TABLE IF NOT EXISTS finance_schema.table_relationships (
    id                  SERIAL PRIMARY KEY,
    source_table        TEXT NOT NULL,
    source_column       TEXT NOT NULL,
    target_schema       TEXT NOT NULL,
    target_table        TEXT NOT NULL,
    target_column       TEXT NOT NULL,
    relationship_text   TEXT NOT NULL,
    constraint_name     VARCHAR(256),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_finance_table_relationships_edge
        UNIQUE (source_table, source_column, target_schema, target_table, target_column)
);

CREATE INDEX IF NOT EXISTS idx_finance_table_relationships_source
    ON finance_schema.table_relationships (source_table);
CREATE INDEX IF NOT EXISTS idx_finance_table_relationships_source_col
    ON finance_schema.table_relationships (source_table, source_column);

COMMENT ON TABLE finance_schema.table_relationships IS 'Foreign keys with referencing tables in finance_schema; target_schema for referenced side';
COMMENT ON COLUMN finance_schema.table_relationships.target_schema IS 'Schema of the referenced (target) table';
COMMENT ON COLUMN finance_schema.table_relationships.relationship_text IS 'Canonical line for LLM context';

-- ============================================================================
-- DONE - Schemas, business tables, app_schema, and FK metadata tables created.
-- Next: load FK rows — python scripts/extract_and_load_relationships.py (requires .env DB access)
-- ============================================================================
