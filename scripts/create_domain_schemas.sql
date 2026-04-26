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
    department_id INT,
    visit_type VARCHAR(50),
    total_cost NUMERIC(14,2)
);
ALTER TABLE healthcare_schema.visits
    ADD COLUMN IF NOT EXISTS department_id INT;

COMMENT ON TABLE healthcare_schema.visits IS 'Records patient visits including admission, discharge, department, and cost information.';
COMMENT ON COLUMN healthcare_schema.visits.visit_id IS 'Unique system-generated identifier for each visit.';
COMMENT ON COLUMN healthcare_schema.visits.patient_id IS 'Foreign key referencing the patient who made the visit.';
COMMENT ON COLUMN healthcare_schema.visits.admission_date IS 'Date when the patient was admitted.';
COMMENT ON COLUMN healthcare_schema.visits.discharge_date IS 'Date when the patient was discharged.';
COMMENT ON COLUMN healthcare_schema.visits.department IS 'Legacy text department name (kept for backward compatibility).';
COMMENT ON COLUMN healthcare_schema.visits.department_id IS 'Foreign key to departments master table.';
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

CREATE TABLE IF NOT EXISTS healthcare_schema.departments (
    department_id SERIAL PRIMARY KEY,
    department_name VARCHAR(100),
    location VARCHAR(100)
);
COMMENT ON TABLE healthcare_schema.departments IS 'Hospital departments such as Cardiology, Emergency, etc.';
COMMENT ON COLUMN healthcare_schema.departments.department_id IS 'Unique identifier for each department';
COMMENT ON COLUMN healthcare_schema.departments.department_name IS 'Name of the department';
COMMENT ON COLUMN healthcare_schema.departments.location IS 'Physical location within hospital';

CREATE TABLE IF NOT EXISTS healthcare_schema.providers (
    provider_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    specialty VARCHAR(100),
    department_id INT REFERENCES healthcare_schema.departments(department_id),
    years_of_experience INT
);
COMMENT ON TABLE healthcare_schema.providers IS 'Healthcare professionals including doctors and nurses';
COMMENT ON COLUMN healthcare_schema.providers.provider_id IS 'Unique identifier for provider';
COMMENT ON COLUMN healthcare_schema.providers.first_name IS 'Provider first name';
COMMENT ON COLUMN healthcare_schema.providers.last_name IS 'Provider last name';
COMMENT ON COLUMN healthcare_schema.providers.specialty IS 'Medical specialization';
COMMENT ON COLUMN healthcare_schema.providers.department_id IS 'Department provider belongs to';
COMMENT ON COLUMN healthcare_schema.providers.years_of_experience IS 'Years of professional experience';

CREATE TABLE IF NOT EXISTS healthcare_schema.procedures (
    procedure_id SERIAL PRIMARY KEY,
    visit_id INT REFERENCES healthcare_schema.visits(visit_id),
    provider_id INT REFERENCES healthcare_schema.providers(provider_id),
    procedure_name VARCHAR(100),
    procedure_date DATE,
    cost DECIMAL(10,2)
);
COMMENT ON TABLE healthcare_schema.procedures IS 'Medical procedures performed during patient visits';
COMMENT ON COLUMN healthcare_schema.procedures.procedure_id IS 'Unique procedure identifier';
COMMENT ON COLUMN healthcare_schema.procedures.visit_id IS 'Associated visit';
COMMENT ON COLUMN healthcare_schema.procedures.provider_id IS 'Provider performing procedure';
COMMENT ON COLUMN healthcare_schema.procedures.procedure_name IS 'Name of procedure';
COMMENT ON COLUMN healthcare_schema.procedures.procedure_date IS 'Date performed';
COMMENT ON COLUMN healthcare_schema.procedures.cost IS 'Cost of procedure';

CREATE TABLE IF NOT EXISTS healthcare_schema.medications (
    medication_id SERIAL PRIMARY KEY,
    medication_name VARCHAR(100),
    manufacturer VARCHAR(100),
    unit_cost DECIMAL(10,2)
);
COMMENT ON TABLE healthcare_schema.medications IS 'Master list of medications';
COMMENT ON COLUMN healthcare_schema.medications.medication_id IS 'Unique medication identifier';
COMMENT ON COLUMN healthcare_schema.medications.medication_name IS 'Name of medication';
COMMENT ON COLUMN healthcare_schema.medications.manufacturer IS 'Manufacturer name';
COMMENT ON COLUMN healthcare_schema.medications.unit_cost IS 'Cost per unit';

CREATE TABLE IF NOT EXISTS healthcare_schema.prescriptions (
    prescription_id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES healthcare_schema.patients(patient_id),
    medication_id INT REFERENCES healthcare_schema.medications(medication_id),
    provider_id INT REFERENCES healthcare_schema.providers(provider_id),
    dosage VARCHAR(50),
    start_date DATE,
    end_date DATE
);
COMMENT ON TABLE healthcare_schema.prescriptions IS 'Prescribed medications for patients';
COMMENT ON COLUMN healthcare_schema.prescriptions.prescription_id IS 'Unique prescription identifier';
COMMENT ON COLUMN healthcare_schema.prescriptions.patient_id IS 'Patient receiving medication';
COMMENT ON COLUMN healthcare_schema.prescriptions.medication_id IS 'Medication prescribed';
COMMENT ON COLUMN healthcare_schema.prescriptions.provider_id IS 'Provider prescribing medication';
COMMENT ON COLUMN healthcare_schema.prescriptions.dosage IS 'Dosage instructions';
COMMENT ON COLUMN healthcare_schema.prescriptions.start_date IS 'Prescription start date';
COMMENT ON COLUMN healthcare_schema.prescriptions.end_date IS 'Prescription end date';

CREATE TABLE IF NOT EXISTS healthcare_schema.billing (
    billing_id SERIAL PRIMARY KEY,
    visit_id INT REFERENCES healthcare_schema.visits(visit_id),
    total_amount DECIMAL(12,2),
    insurance_covered_amount DECIMAL(12,2),
    out_of_pocket_amount DECIMAL(12,2),
    billing_date DATE
);
COMMENT ON TABLE healthcare_schema.billing IS 'Billing details for each visit';
COMMENT ON COLUMN healthcare_schema.billing.billing_id IS 'Unique billing identifier';
COMMENT ON COLUMN healthcare_schema.billing.visit_id IS 'Visit being billed';
COMMENT ON COLUMN healthcare_schema.billing.total_amount IS 'Total billed amount';
COMMENT ON COLUMN healthcare_schema.billing.insurance_covered_amount IS 'Amount covered by insurance';
COMMENT ON COLUMN healthcare_schema.billing.out_of_pocket_amount IS 'Amount paid by patient';
COMMENT ON COLUMN healthcare_schema.billing.billing_date IS 'Billing date';

CREATE TABLE IF NOT EXISTS healthcare_schema.insurance_claims (
    claim_id SERIAL PRIMARY KEY,
    visit_id INT REFERENCES healthcare_schema.visits(visit_id),
    patient_id INT REFERENCES healthcare_schema.patients(patient_id),
    claim_status VARCHAR(50),
    claim_amount DECIMAL(12,2),
    approved_amount DECIMAL(12,2),
    claim_date DATE
);
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
    category_id INT,
    brand VARCHAR(100),
    price NUMERIC(10,2),
    launch_date DATE
);
ALTER TABLE retail_schema.products
    ADD COLUMN IF NOT EXISTS category_id INT;

COMMENT ON TABLE retail_schema.products IS 'Stores product catalog information including category, brand, and pricing.';
COMMENT ON COLUMN retail_schema.products.product_id IS 'Unique system-generated identifier for each product.';
COMMENT ON COLUMN retail_schema.products.product_name IS 'Name of the product.';
COMMENT ON COLUMN retail_schema.products.category IS 'Legacy text category (kept for backward compatibility).';
COMMENT ON COLUMN retail_schema.products.category_id IS 'Foreign key to categories hierarchy.';
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

CREATE TABLE IF NOT EXISTS retail_schema.categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100),
    parent_category_id INT REFERENCES retail_schema.categories(category_id)
);
COMMENT ON TABLE retail_schema.categories IS 'Product category hierarchy';
COMMENT ON COLUMN retail_schema.categories.category_id IS 'Unique category identifier';
COMMENT ON COLUMN retail_schema.categories.category_name IS 'Category name';
COMMENT ON COLUMN retail_schema.categories.parent_category_id IS 'Parent category for hierarchical grouping';

CREATE TABLE IF NOT EXISTS retail_schema.suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(100),
    contact_email VARCHAR(100),
    phone VARCHAR(20),
    city VARCHAR(50),
    state VARCHAR(50)
);
COMMENT ON TABLE retail_schema.suppliers IS 'Suppliers providing products';
COMMENT ON COLUMN retail_schema.suppliers.supplier_id IS 'Unique supplier identifier';
COMMENT ON COLUMN retail_schema.suppliers.supplier_name IS 'Supplier name';
COMMENT ON COLUMN retail_schema.suppliers.contact_email IS 'Supplier contact email';
COMMENT ON COLUMN retail_schema.suppliers.phone IS 'Supplier phone number';
COMMENT ON COLUMN retail_schema.suppliers.city IS 'Supplier city';
COMMENT ON COLUMN retail_schema.suppliers.state IS 'Supplier state';

CREATE TABLE IF NOT EXISTS retail_schema.stores (
    store_id SERIAL PRIMARY KEY,
    store_name VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    store_type VARCHAR(50)
);
COMMENT ON TABLE retail_schema.stores IS 'Retail store locations';
COMMENT ON COLUMN retail_schema.stores.store_id IS 'Unique store identifier';
COMMENT ON COLUMN retail_schema.stores.store_name IS 'Store name';
COMMENT ON COLUMN retail_schema.stores.city IS 'Store city';
COMMENT ON COLUMN retail_schema.stores.state IS 'Store state';
COMMENT ON COLUMN retail_schema.stores.store_type IS 'Type (online/physical)';

CREATE TABLE IF NOT EXISTS retail_schema.inventory (
    inventory_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES retail_schema.products(product_id),
    store_id INT REFERENCES retail_schema.stores(store_id),
    stock_quantity INT,
    last_updated TIMESTAMP
);
COMMENT ON TABLE retail_schema.inventory IS 'Inventory levels per product and store';
COMMENT ON COLUMN retail_schema.inventory.inventory_id IS 'Unique inventory record';
COMMENT ON COLUMN retail_schema.inventory.product_id IS 'Product being tracked';
COMMENT ON COLUMN retail_schema.inventory.store_id IS 'Store holding inventory';
COMMENT ON COLUMN retail_schema.inventory.stock_quantity IS 'Available stock quantity';
COMMENT ON COLUMN retail_schema.inventory.last_updated IS 'Last update timestamp';

CREATE TABLE IF NOT EXISTS retail_schema.shipments (
    shipment_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES retail_schema.orders(order_id),
    shipment_date DATE,
    delivery_date DATE,
    shipment_status VARCHAR(50)
);
COMMENT ON TABLE retail_schema.shipments IS 'Tracks shipment and delivery of orders';
COMMENT ON COLUMN retail_schema.shipments.shipment_id IS 'Unique shipment identifier';
COMMENT ON COLUMN retail_schema.shipments.order_id IS 'Order being shipped';
COMMENT ON COLUMN retail_schema.shipments.shipment_date IS 'Date shipped';
COMMENT ON COLUMN retail_schema.shipments.delivery_date IS 'Date delivered';
COMMENT ON COLUMN retail_schema.shipments.shipment_status IS 'Delivery status';

CREATE TABLE IF NOT EXISTS retail_schema.reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES retail_schema.products(product_id),
    customer_id INT REFERENCES retail_schema.customers(customer_id),
    rating INT,
    review_text TEXT,
    review_date DATE
);
COMMENT ON TABLE retail_schema.reviews IS 'Customer reviews and ratings for products';
COMMENT ON COLUMN retail_schema.reviews.review_id IS 'Unique review identifier';
COMMENT ON COLUMN retail_schema.reviews.product_id IS 'Reviewed product';
COMMENT ON COLUMN retail_schema.reviews.customer_id IS 'Customer writing review';
COMMENT ON COLUMN retail_schema.reviews.rating IS 'Rating score (1-5)';
COMMENT ON COLUMN retail_schema.reviews.review_text IS 'Written feedback';
COMMENT ON COLUMN retail_schema.reviews.review_date IS 'Date of review';

CREATE TABLE IF NOT EXISTS retail_schema.promotions (
    promotion_id SERIAL PRIMARY KEY,
    promotion_name VARCHAR(100),
    discount_percentage DECIMAL(5,2),
    start_date DATE,
    end_date DATE
);
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

COMMENT ON TABLE finance_schema.accounts IS 'Stores customer bank account information including account type, branch location, and current balance.';
COMMENT ON COLUMN finance_schema.accounts.account_id IS 'Unique system-generated identifier assigned to each bank account.';
COMMENT ON COLUMN finance_schema.accounts.customer_name IS 'Legacy customer name text (kept for backward compatibility).';
COMMENT ON COLUMN finance_schema.accounts.customer_id IS 'Foreign key to finance customers master.';
COMMENT ON COLUMN finance_schema.accounts.account_type IS 'Type of bank account such as savings or checking.';
COMMENT ON COLUMN finance_schema.accounts.branch_city IS 'Legacy branch city text (kept for backward compatibility).';
COMMENT ON COLUMN finance_schema.accounts.branch_id IS 'Foreign key to branch master.';
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
COMMENT ON TABLE finance_schema.customers IS 'Customer master data storing personal and contact details';
COMMENT ON COLUMN finance_schema.customers.customer_id IS 'Unique identifier for each customer';
COMMENT ON COLUMN finance_schema.customers.first_name IS 'Customer first name';
COMMENT ON COLUMN finance_schema.customers.last_name IS 'Customer last name';
COMMENT ON COLUMN finance_schema.customers.email IS 'Customer email address';
COMMENT ON COLUMN finance_schema.customers.phone IS 'Customer phone number';
COMMENT ON COLUMN finance_schema.customers.city IS 'City where customer resides';
COMMENT ON COLUMN finance_schema.customers.state IS 'State where customer resides';
COMMENT ON COLUMN finance_schema.customers.created_at IS 'Timestamp when customer profile was created';

CREATE TABLE IF NOT EXISTS finance_schema.branches (
    branch_id SERIAL PRIMARY KEY,
    branch_name VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50)
);
COMMENT ON TABLE finance_schema.branches IS 'Bank branch information';
COMMENT ON COLUMN finance_schema.branches.branch_id IS 'Unique identifier for branch';
COMMENT ON COLUMN finance_schema.branches.branch_name IS 'Name of the branch';
COMMENT ON COLUMN finance_schema.branches.city IS 'City where branch is located';
COMMENT ON COLUMN finance_schema.branches.state IS 'State where branch is located';

CREATE TABLE IF NOT EXISTS finance_schema.credit_cards (
    card_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES finance_schema.customers(customer_id),
    card_type VARCHAR(50),
    credit_limit DECIMAL(12,2),
    current_balance DECIMAL(12,2),
    issue_date DATE,
    expiry_date DATE
);
COMMENT ON TABLE finance_schema.credit_cards IS 'Credit card accounts issued to customers';
COMMENT ON COLUMN finance_schema.credit_cards.card_id IS 'Unique credit card identifier';
COMMENT ON COLUMN finance_schema.credit_cards.customer_id IS 'Customer owning the card';
COMMENT ON COLUMN finance_schema.credit_cards.card_type IS 'Type of card (e.g., Visa, Mastercard)';
COMMENT ON COLUMN finance_schema.credit_cards.credit_limit IS 'Maximum allowed spending limit';
COMMENT ON COLUMN finance_schema.credit_cards.current_balance IS 'Outstanding balance on the card';
COMMENT ON COLUMN finance_schema.credit_cards.issue_date IS 'Date when card was issued';
COMMENT ON COLUMN finance_schema.credit_cards.expiry_date IS 'Card expiration date';

CREATE TABLE IF NOT EXISTS finance_schema.payments (
    payment_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES finance_schema.accounts(account_id),
    loan_id INT REFERENCES finance_schema.loans(loan_id),
    payment_amount DECIMAL(12,2),
    payment_date DATE,
    payment_type VARCHAR(50)
);
COMMENT ON TABLE finance_schema.payments IS 'Payments made towards loans or accounts';
COMMENT ON COLUMN finance_schema.payments.payment_id IS 'Unique payment identifier';
COMMENT ON COLUMN finance_schema.payments.account_id IS 'Account from which payment was made';
COMMENT ON COLUMN finance_schema.payments.loan_id IS 'Loan associated with payment (if applicable)';
COMMENT ON COLUMN finance_schema.payments.payment_amount IS 'Amount paid';
COMMENT ON COLUMN finance_schema.payments.payment_date IS 'Date of payment';
COMMENT ON COLUMN finance_schema.payments.payment_type IS 'Type of payment (EMI, credit card, etc.)';

CREATE TABLE IF NOT EXISTS finance_schema.investment_accounts (
    investment_account_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES finance_schema.customers(customer_id),
    account_type VARCHAR(50),
    total_value DECIMAL(14,2),
    created_at TIMESTAMP
);
COMMENT ON TABLE finance_schema.investment_accounts IS 'Investment portfolios held by customers';
COMMENT ON COLUMN finance_schema.investment_accounts.investment_account_id IS 'Unique investment account identifier';
COMMENT ON COLUMN finance_schema.investment_accounts.customer_id IS 'Customer owning investment account';
COMMENT ON COLUMN finance_schema.investment_accounts.account_type IS 'Type of investment (stocks, mutual funds)';
COMMENT ON COLUMN finance_schema.investment_accounts.total_value IS 'Total portfolio value';
COMMENT ON COLUMN finance_schema.investment_accounts.created_at IS 'Account creation timestamp';

CREATE TABLE IF NOT EXISTS finance_schema.account_balances_history (
    record_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES finance_schema.accounts(account_id),
    balance DECIMAL(12,2),
    recorded_at TIMESTAMP
);
COMMENT ON TABLE finance_schema.account_balances_history IS 'Historical record of account balances';
COMMENT ON COLUMN finance_schema.account_balances_history.record_id IS 'Unique record identifier';
COMMENT ON COLUMN finance_schema.account_balances_history.account_id IS 'Account being tracked';
COMMENT ON COLUMN finance_schema.account_balances_history.balance IS 'Balance at given timestamp';
COMMENT ON COLUMN finance_schema.account_balances_history.recorded_at IS 'Timestamp of recorded balance';

CREATE TABLE IF NOT EXISTS finance_schema.fraud_alerts (
    alert_id SERIAL PRIMARY KEY,
    transaction_id INT REFERENCES finance_schema.transactions(transaction_id),
    alert_type VARCHAR(50),
    alert_status VARCHAR(50),
    created_at TIMESTAMP
);
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
