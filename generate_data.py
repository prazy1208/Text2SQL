"""
Generate synthetic data for healthcare_schema, retail_schema, and finance_schema.
Uses Faker, pandas, and SQLAlchemy. Loads DB credentials from .env.
Run: python generate_data.py
"""

import logging
import os
from datetime import timedelta

import pandas as pd
from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load .env before reading env vars
load_dotenv()

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def get_engine():
    """Build SQLAlchemy engine from .env (DATABASE_URL or DB_* variables)."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url)
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "postgres")
    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


def _sync_sequence(engine, schema: str, table: str, column: str):
    """Set the table's SERIAL sequence to the current max value."""
    stmt = text(
        f"SELECT setval(pg_get_serial_sequence('{schema}.{table}', '{column}'), "
        f"(SELECT COALESCE(MAX({column}), 1) FROM {schema}.{table}))"
    )
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


# ---------------------------------------------------------------------------
# Healthcare
# ---------------------------------------------------------------------------

INSURANCE_TYPES = ["Medicare", "Medicaid", "Private", "Employer", "Uninsured"]
GENDERS = ["Male", "Female", "Other"]
DEPARTMENTS = ["Emergency", "Surgery", "Cardiology", "Neurology", "Pediatrics", "Oncology", "General"]
VISIT_TYPES = ["Inpatient", "Outpatient", "Emergency", "Follow-up"]
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
DIAGNOSIS_CODES = ["ICD-10-A01", "ICD-10-B02", "ICD-10-C03", "ICD-10-D04", "ICD-10-E05", "ICD-10-F06", "ICD-10-G07", "ICD-10-H08"]


def generate_healthcare_data(engine):
    """Generate patients (1000), visits (2000), diagnoses (3000) in healthcare_schema."""
    fake = Faker()
    fake.seed_instance(42)
    logger.info("Generating healthcare_schema data...")

    # Patients: 1000
    n_patients = 1000
    patients = []
    for i in range(1, n_patients + 1):
        reg_date = fake.date_between(start_date="-5y", end_date="today")
        dob = fake.date_between(start_date="-90y", end_date="-18y")
        patients.append({
            "patient_id": i,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "date_of_birth": dob,
            "gender": fake.random_element(GENDERS),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "insurance_type": fake.random_element(INSURANCE_TYPES),
            "registration_date": reg_date,
        })
    df_patients = pd.DataFrame(patients)
    df_patients.to_sql("patients", engine, schema="healthcare_schema", if_exists="append", index=False)
    logger.info("  Inserted %d patients.", len(df_patients))

    # Visits: 2000 (linked to patients)
    n_visits = 2000
    visits = []
    for i in range(1, n_visits + 1):
        patient_id = fake.random_int(min=1, max=n_patients)
        admission = fake.date_between(start_date="-2y", end_date="today")
        discharge = admission + timedelta(days=fake.random_int(min=0, max=14))
        cost = round(float(fake.random_number(digits=4, fix_len=False)) + fake.random.random() * 100, 2)
        visits.append({
            "visit_id": i,
            "patient_id": patient_id,
            "admission_date": admission,
            "discharge_date": discharge,
            "department": fake.random_element(DEPARTMENTS),
            "visit_type": fake.random_element(VISIT_TYPES),
            "total_cost": cost,
        })
    df_visits = pd.DataFrame(visits)
    df_visits.to_sql("visits", engine, schema="healthcare_schema", if_exists="append", index=False)
    logger.info("  Inserted %d visits.", len(df_visits))

    # Diagnoses: 3000 (linked to visits)
    n_diagnoses = 3000
    diagnoses = []
    for i in range(1, n_diagnoses + 1):
        visit_id = fake.random_int(min=1, max=n_visits)
        code = fake.random_element(DIAGNOSIS_CODES) + "-" + str(fake.random_int(10, 99))
        diagnoses.append({
            "diagnosis_id": i,
            "visit_id": visit_id,
            "diagnosis_code": code,
            "diagnosis_description": fake.sentence(nb_words=6),
            "severity_level": fake.random_element(SEVERITY_LEVELS),
        })
    df_diagnoses = pd.DataFrame(diagnoses)
    df_diagnoses.to_sql("diagnoses", engine, schema="healthcare_schema", if_exists="append", index=False)
    logger.info("  Inserted %d diagnoses.", len(df_diagnoses))
    for tbl, col in [("patients", "patient_id"), ("visits", "visit_id"), ("diagnoses", "diagnosis_id")]:
        _sync_sequence(engine, "healthcare_schema", tbl, col)
    logger.info("Healthcare data generation complete.")


# ---------------------------------------------------------------------------
# Retail
# ---------------------------------------------------------------------------

CATEGORIES = ["Electronics", "Clothing", "Home", "Sports", "Books", "Toys", "Health", "Grocery"]
BRANDS = ["Acme", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Omega"]


def generate_retail_data(engine):
    """Generate customers (1000), products (500), orders (3000) in retail_schema."""
    fake = Faker()
    fake.seed_instance(43)
    logger.info("Generating retail_schema data...")

    # Customers: 1000
    n_customers = 1000
    customers = []
    for i in range(1, n_customers + 1):
        first, last = fake.first_name(), fake.last_name()
        customers.append({
            "customer_id": i,
            "first_name": first,
            "last_name": last,
            "email": fake.ascii_safe_email(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "signup_date": fake.date_between(start_date="-3y", end_date="today"),
        })
    df_customers = pd.DataFrame(customers)
    df_customers.to_sql("customers", engine, schema="retail_schema", if_exists="append", index=False)
    logger.info("  Inserted %d customers.", len(df_customers))

    # Products: 500
    n_products = 500
    products = []
    for i in range(1, n_products + 1):
        price = round(fake.random.uniform(5.0, 500.0), 2)
        products.append({
            "product_id": i,
            "product_name": fake.catch_phrase().replace(".", ""),
            "category": fake.random_element(CATEGORIES),
            "brand": fake.random_element(BRANDS),
            "price": price,
            "launch_date": fake.date_between(start_date="-4y", end_date="today"),
        })
    df_products = pd.DataFrame(products)
    df_products.to_sql("products", engine, schema="retail_schema", if_exists="append", index=False)
    logger.info("  Inserted %d products.", len(df_products))

    # Orders: 3000 (linked to customers and products)
    n_orders = 3000
    orders = []
    for i in range(1, n_orders + 1):
        customer_id = fake.random_int(min=1, max=n_customers)
        product_id = fake.random_int(min=1, max=n_products)
        quantity = fake.random_int(min=1, max=10)
        # Price looked up would require a join; use a plausible total
        unit_price = fake.random.uniform(5.0, 500.0)
        total_amount = round(quantity * unit_price, 2)
        orders.append({
            "order_id": i,
            "customer_id": customer_id,
            "product_id": product_id,
            "order_date": fake.date_between(start_date="-2y", end_date="today"),
            "quantity": quantity,
            "total_amount": total_amount,
        })
    df_orders = pd.DataFrame(orders)
    df_orders.to_sql("orders", engine, schema="retail_schema", if_exists="append", index=False)
    logger.info("  Inserted %d orders.", len(df_orders))
    for tbl, col in [("customers", "customer_id"), ("products", "product_id"), ("orders", "order_id")]:
        _sync_sequence(engine, "retail_schema", tbl, col)
    logger.info("Retail data generation complete.")


# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------

ACCOUNT_TYPES = ["savings", "checking"]
TRANSACTION_TYPES = ["debit", "credit"]
LOAN_TYPES = ["home", "auto", "personal"]


def generate_finance_data(engine):
    """Generate accounts (1000), transactions (5000), loans (800) in finance_schema."""
    fake = Faker()
    fake.seed_instance(44)
    logger.info("Generating finance_schema data...")

    # Accounts: 1000
    n_accounts = 1000
    accounts = []
    for i in range(1, n_accounts + 1):
        balance = round(fake.random.uniform(100.0, 100000.0), 2)
        accounts.append({
            "account_id": i,
            "customer_name": fake.name(),
            "account_type": fake.random_element(ACCOUNT_TYPES),
            "branch_city": fake.city(),
            "opening_date": fake.date_between(start_date="-10y", end_date="today"),
            "current_balance": balance,
        })
    df_accounts = pd.DataFrame(accounts)
    df_accounts.to_sql("accounts", engine, schema="finance_schema", if_exists="append", index=False)
    logger.info("  Inserted %d accounts.", len(df_accounts))

    # Transactions: 5000 (linked to accounts)
    n_transactions = 5000
    transactions = []
    for i in range(1, n_transactions + 1):
        account_id = fake.random_int(min=1, max=n_accounts)
        ttype = fake.random_element(TRANSACTION_TYPES)
        amount = round(fake.random.uniform(10.0, 5000.0), 2)
        transactions.append({
            "transaction_id": i,
            "account_id": account_id,
            "transaction_date": fake.date_between(start_date="-1y", end_date="today"),
            "transaction_type": ttype,
            "amount": amount,
            "description": fake.sentence(nb_words=4),
        })
    df_transactions = pd.DataFrame(transactions)
    df_transactions.to_sql("transactions", engine, schema="finance_schema", if_exists="append", index=False)
    logger.info("  Inserted %d transactions.", len(df_transactions))

    # Loans: 800 (linked to accounts)
    n_loans = 800
    loans = []
    for i in range(1, n_loans + 1):
        account_id = fake.random_int(min=1, max=n_accounts)
        start_date = fake.date_between(start_date="-5y", end_date="today")
        end_date = start_date + timedelta(days=fake.random_int(365, 3600))
        loan_amount = round(fake.random.uniform(5000.0, 500000.0), 2)
        rate = round(fake.random.uniform(3.0, 15.0), 2)
        loans.append({
            "loan_id": i,
            "account_id": account_id,
            "loan_type": fake.random_element(LOAN_TYPES),
            "loan_amount": loan_amount,
            "interest_rate": rate,
            "loan_start_date": start_date,
            "loan_end_date": end_date,
        })
    df_loans = pd.DataFrame(loans)
    df_loans.to_sql("loans", engine, schema="finance_schema", if_exists="append", index=False)
    logger.info("  Inserted %d loans.", len(df_loans))
    for tbl, col in [("accounts", "account_id"), ("transactions", "transaction_id"), ("loans", "loan_id")]:
        _sync_sequence(engine, "finance_schema", tbl, col)
    logger.info("Finance data generation complete.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting data generation.")
    engine = get_engine()
    generate_healthcare_data(engine)
    generate_retail_data(engine)
    generate_finance_data(engine)
    logger.info("All data generation finished.")
