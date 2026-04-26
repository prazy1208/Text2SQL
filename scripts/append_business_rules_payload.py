"""
Append provided business rules into domain business_rules tables.

This script intentionally ignores incoming index/rule_id values and inserts only:
concept_name, description, insight, keywords.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def get_engine():
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


def to_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "concept_name": item["concept_name"],
            "description": item["description"],
            "insight": item["insight"],
            "keywords": item["keywords"],
        }
        for item in items
    ]


FINANCE_RULES = [
    {"concept_name": "Credit Utilization Analysis", "description": "Calculates credit card utilization by comparing current_balance against credit_limit from credit_cards table to identify usage patterns.", "insight": "Enables Text2SQL to answer queries about customer credit health, overspending risks, and credit availability across different card types.", "keywords": ["credit utilization", "credit limit usage", "card balance ratio"]},
    {"concept_name": "Loan Repayment Tracking", "description": "Monitors loan payment progress by joining loans and payments tables to track payment_amount against loan_amount over time.", "insight": "Supports queries about outstanding loan balances, payment completion rates, and delinquency identification for risk assessment.", "keywords": ["loan payments", "repayment status", "outstanding balance"]},
    {"concept_name": "Fraud Detection Metrics", "description": "Analyzes fraud_alerts by alert_type, alert_status, and linked transaction_id to measure fraud incident rates and resolution efficiency.", "insight": "Enables Text2SQL to identify fraud patterns, response times, and high-risk transaction types for security monitoring.", "keywords": ["fraud alerts", "suspicious transactions", "fraud detection rate"]},
    {"concept_name": "Investment Portfolio Performance", "description": "Tracks total_value trends in investment_accounts by account_type and customer_id to measure portfolio growth and allocation.", "insight": "Supports queries about investment returns, portfolio diversification, and customer wealth accumulation patterns.", "keywords": ["investment performance", "portfolio value", "investment growth"]},
    {"concept_name": "Branch Performance Comparison", "description": "Aggregates account and transaction metrics by branch_id from branches table to compare city and state level banking activity.", "insight": "Enables geographic performance analysis, identifying high-performing branches and regional market opportunities.", "keywords": ["branch performance", "regional banking", "branch comparison"]},
    {"concept_name": "Account Balance Volatility", "description": "Analyzes balance fluctuations in account_balances_history by tracking recorded_at timestamps to identify stability patterns.", "insight": "Helps detect unusual account activity, cash flow issues, and accounts requiring attention or financial advisory services.", "keywords": ["balance changes", "account volatility", "balance history"]},
    {"concept_name": "Customer Relationship Tenure", "description": "Calculates customer lifetime by comparing created_at in customers table and opening_date in accounts to measure relationship duration.", "insight": "Supports customer segmentation queries, loyalty analysis, and retention strategy effectiveness measurement.", "keywords": ["customer tenure", "relationship duration", "customer age"]},
    {"concept_name": "Multi-Product Customer Profiling", "description": "Identifies customers with multiple products by joining accounts, credit_cards, loans, and investment_accounts on customer_id.", "insight": "Enables cross-selling analysis, product penetration metrics, and identification of high-value multi-product customers.", "keywords": ["product holdings", "cross-product ownership", "customer products"]},
    {"concept_name": "Loan Interest Revenue Potential", "description": "Calculates expected interest revenue by multiplying loan_amount by interest_rate and loan duration from loans table.", "insight": "Supports revenue forecasting, loan portfolio profitability analysis, and pricing strategy optimization queries.", "keywords": ["loan interest", "interest revenue", "loan profitability"]},
    {"concept_name": "Payment Method Preferences", "description": "Analyzes payment_type distribution from payments table to identify preferred payment channels and methods by customer segments.", "insight": "Enables Text2SQL to answer queries about payment behavior, channel optimization, and customer convenience patterns.", "keywords": ["payment methods", "payment channels", "payment preferences"]},
    {"concept_name": "Credit Card Expiry Management", "description": "Tracks expiry_date in credit_cards table to identify cards nearing expiration and renewal timing patterns.", "insight": "Supports proactive customer communication queries, renewal campaign targeting, and card lifecycle management.", "keywords": ["card expiry", "card renewal", "expiring cards"]},
    {"concept_name": "Geographic Customer Distribution", "description": "Aggregates customer counts by city and state from customers table to analyze market penetration and demographic spread.", "insight": "Enables market analysis queries, branch expansion planning, and regional marketing strategy optimization.", "keywords": ["customer geography", "market distribution", "regional customers"]},
    {"concept_name": "Account Type Diversification", "description": "Analyzes account_type distribution across accounts and investment_accounts tables to measure product mix and preferences.", "insight": "Supports product portfolio queries, identifies gaps in account type offerings, and guides product development priorities.", "keywords": ["account types", "product mix", "account distribution"]},
    {"concept_name": "Loan Maturity Schedule", "description": "Tracks loan_end_date from loans table to forecast upcoming loan completions and refinancing opportunities.", "insight": "Enables cash flow forecasting, renewal opportunity identification, and loan book maturity analysis queries.", "keywords": ["loan maturity", "loan end dates", "maturing loans"]},
    {"concept_name": "Transaction-to-Fraud Correlation", "description": "Links transaction_id between transactions and fraud_alerts tables to calculate fraud rate by transaction_type and amount ranges.", "insight": "Supports risk profiling queries, identifies vulnerable transaction categories, and improves fraud prevention targeting.", "keywords": ["fraud by transaction type", "transaction fraud rate", "risky transactions"]},
    {"concept_name": "Customer Contact Completeness", "description": "Evaluates email and phone field population in customers table to measure contact information quality and completeness.", "insight": "Enables data quality queries, identifies communication gaps, and supports customer outreach effectiveness analysis.", "keywords": ["contact information", "customer reachability", "data completeness"]},
    {"concept_name": "Branch Account Concentration", "description": "Calculates account concentration by branch_id from accounts table to identify branch capacity and workload distribution.", "insight": "Supports operational efficiency queries, staffing optimization, and identifies underutilized or overburdened branches.", "keywords": ["accounts per branch", "branch concentration", "branch workload"]},
    {"concept_name": "Payment Timeliness Analysis", "description": "Compares payment_date from payments table against loan payment schedules to measure on-time payment rates and delays.", "insight": "Enables delinquency tracking, credit risk assessment, and customer payment behavior pattern identification.", "keywords": ["payment punctuality", "late payments", "payment timeliness"]},
    {"concept_name": "Credit Card Issuance Trends", "description": "Analyzes issue_date patterns in credit_cards table by card_type to identify seasonal issuance trends and growth patterns.", "insight": "Supports acquisition campaign analysis, identifies successful card launch periods, and guides promotional timing.", "keywords": ["card issuance", "new cards", "card acquisition"]},
    {"concept_name": "Customer Transaction Recency", "description": "Identifies time since last transaction by customer_id using transaction_date from transactions table to detect dormant accounts.", "insight": "Enables customer engagement queries, churn prediction, and reactivation campaign targeting for inactive customers.", "keywords": ["transaction recency", "last transaction", "dormant accounts"]},
]

RETAIL_RULES = [
    {"concept_name": "Inventory Stock Health", "description": "Monitors stock_quantity levels in inventory table by product_id and store_id to identify low stock, overstock, and optimal inventory positions.", "insight": "Enables Text2SQL to answer queries about stockouts, replenishment needs, and inventory optimization across store locations.", "keywords": ["stock levels", "inventory status", "out of stock"]},
    {"concept_name": "Product Review Sentiment", "description": "Analyzes rating distribution and review_text from reviews table by product_id to measure customer satisfaction and product quality perception.", "insight": "Supports queries about product ratings, customer feedback trends, and identifies products needing quality improvements or promotion.", "keywords": ["product ratings", "customer reviews", "review scores"]},
    {"concept_name": "Shipment Delivery Performance", "description": "Calculates delivery time by comparing shipment_date and delivery_date in shipments table to measure fulfillment speed and reliability.", "insight": "Enables delivery performance analysis, identifies shipping delays, and supports logistics optimization queries.", "keywords": ["delivery time", "shipping speed", "fulfillment performance"]},
    {"concept_name": "Promotion Effectiveness", "description": "Links promotion_id with order_date to measure sales lift during promotion periods by analyzing discount_percentage impact from promotions table.", "insight": "Supports ROI analysis of promotional campaigns, identifies most effective discounts, and guides pricing strategy decisions.", "keywords": ["promotion impact", "discount effectiveness", "campaign performance"]},
    {"concept_name": "Store Performance Comparison", "description": "Aggregates orders and inventory metrics by store_id from stores table to compare sales and stock efficiency across locations and store_type.", "insight": "Enables geographic performance queries, identifies top-performing stores, and supports expansion or closure decisions.", "keywords": ["store performance", "location comparison", "store sales"]},
    {"concept_name": "Category Hierarchy Navigation", "description": "Uses parent_category_id relationships in categories table to analyze product distribution and sales across category levels and subcategories.", "insight": "Supports hierarchical category queries, identifies category performance at different levels, and enables drill-down analysis.", "keywords": ["category hierarchy", "subcategories", "category levels"]},
    {"concept_name": "Supplier Geographic Distribution", "description": "Analyzes supplier locations by city and state from suppliers table to measure supply chain geographic diversity and regional dependencies.", "insight": "Enables supply chain risk assessment, identifies geographic concentration, and supports supplier diversification strategies.", "keywords": ["supplier locations", "supplier geography", "supply chain distribution"]},
    {"concept_name": "Inventory Freshness Tracking", "description": "Monitors last_updated timestamps in inventory table to identify stale inventory records and data accuracy across stores.", "insight": "Supports inventory data quality queries, identifies stores with outdated records, and ensures real-time stock visibility.", "keywords": ["inventory updates", "stock freshness", "last updated"]},
    {"concept_name": "Customer Review Engagement", "description": "Calculates review submission rates by comparing customers who purchased versus those who left reviews using customer_id from reviews table.", "insight": "Enables engagement analysis, identifies products generating buzz, and measures customer feedback participation rates.", "keywords": ["review participation", "customer feedback rate", "review engagement"]},
    {"concept_name": "Order Fulfillment Status", "description": "Tracks shipment_status from shipments table linked to order_id to monitor pending, shipped, and delivered order completion rates.", "insight": "Supports operational queries about order pipeline, identifies fulfillment bottlenecks, and measures customer service efficiency.", "keywords": ["order status", "fulfillment tracking", "shipment progress"]},
    {"concept_name": "Product Launch Success", "description": "Analyzes order volume and review ratings for products within periods after launch_date from products table to measure new product adoption.", "insight": "Enables new product performance queries, identifies successful launches, and guides future product development priorities.", "keywords": ["new product performance", "launch success", "product adoption"]},
    {"concept_name": "Multi-Store Inventory Distribution", "description": "Compares stock_quantity across store_id in inventory table for same product_id to identify inventory allocation imbalances.", "insight": "Supports inventory rebalancing queries, identifies overstocked and understocked locations, and optimizes stock distribution.", "keywords": ["inventory allocation", "stock distribution", "multi-location inventory"]},
    {"concept_name": "Customer Geographic Penetration", "description": "Maps customer distribution by city and state from customers table against store locations to identify underserved markets.", "insight": "Enables market gap analysis, supports expansion planning, and identifies opportunities for new store openings.", "keywords": ["customer geography", "market coverage", "regional customers"]},
    {"concept_name": "Average Order Value Trends", "description": "Calculates mean total_amount from orders table over time periods to track customer spending patterns and basket size evolution.", "insight": "Supports pricing strategy queries, identifies upselling opportunities, and measures promotional impact on transaction size.", "keywords": ["average order value", "basket size", "transaction amount"]},
    {"concept_name": "Product Price Positioning", "description": "Analyzes price distribution within category_id and brand from products table to identify premium, mid-range, and budget positioning.", "insight": "Enables competitive pricing queries, identifies pricing gaps, and supports assortment strategy and margin optimization.", "keywords": ["price points", "pricing tiers", "product pricing"]},
    {"concept_name": "Promotion Timing Patterns", "description": "Examines start_date and end_date patterns in promotions table to identify seasonal promotion strategies and campaign frequency.", "insight": "Supports promotional calendar analysis, identifies optimal timing windows, and guides future campaign scheduling.", "keywords": ["promotion schedule", "campaign timing", "promotional periods"]},
    {"concept_name": "Customer Lifetime Value", "description": "Aggregates total_amount from orders table by customer_id over their tenure since signup_date to calculate cumulative customer value.", "insight": "Enables customer segmentation queries, identifies high-value customers, and supports retention investment prioritization.", "keywords": ["customer value", "lifetime spending", "customer worth"]},
    {"concept_name": "Review Recency Analysis", "description": "Tracks time since last review_date by product_id from reviews table to identify products with recent feedback versus stale reviews.", "insight": "Supports review freshness queries, identifies products needing review solicitation, and measures ongoing customer engagement.", "keywords": ["recent reviews", "review freshness", "latest feedback"]},
    {"concept_name": "Store Type Performance Segmentation", "description": "Compares sales metrics and inventory turnover by store_type from stores table to analyze performance across different retail formats.", "insight": "Enables retail format comparison, identifies optimal store models, and guides format expansion or conversion strategies.", "keywords": ["store format", "store type performance", "retail format"]},
    {"concept_name": "Supplier Contact Accessibility", "description": "Evaluates contact_email and phone completeness in suppliers table to measure supplier communication readiness and data quality.", "insight": "Supports supply chain communication queries, identifies suppliers needing updated contact information, and ensures procurement efficiency.", "keywords": ["supplier contacts", "supplier reachability", "contact completeness"]},
]

HEALTHCARE_RULES = [
    {"concept_name": "Insurance Claim Approval Rate", "description": "Analyzes claim_status from insurance_claims table comparing approved_amount to claim_amount to measure claim acceptance and denial patterns.", "insight": "Enables Text2SQL to answer queries about claim success rates, identifies problematic claim types, and supports revenue cycle optimization.", "keywords": ["claim approval", "claim denial rate", "insurance acceptance"]},
    {"concept_name": "Medication Cost Analysis", "description": "Tracks unit_cost and manufacturer from medications table to compare pricing across brands and identify cost-effective treatment alternatives.", "insight": "Supports formulary optimization queries, identifies high-cost medications, and enables pharmaceutical cost management strategies.", "keywords": ["medication costs", "drug pricing", "pharmaceutical expenses"]},
    {"concept_name": "Provider Specialization Workload", "description": "Aggregates visits, procedures, and prescriptions by provider_id and specialty from providers table to measure specialist utilization and capacity.", "insight": "Enables provider capacity planning, identifies overburdened specialists, and supports workforce allocation decisions.", "keywords": ["provider workload", "specialist capacity", "physician utilization"]},
    {"concept_name": "Diagnosis Severity Distribution", "description": "Analyzes severity_level patterns in diagnoses table by diagnosis_code to measure acuity mix and case complexity across departments.", "insight": "Supports case mix analysis, resource planning for high-acuity patients, and quality of care risk adjustment.", "keywords": ["diagnosis severity", "case complexity", "patient acuity"]},
    {"concept_name": "Billing Payment Gap Analysis", "description": "Compares total_amount against insurance_covered_amount and out_of_pocket_amount in billing table to identify payment collection opportunities.", "insight": "Enables revenue cycle queries, identifies uncollected balances, and supports financial counseling and payment plan targeting.", "keywords": ["payment gaps", "billing balance", "collection opportunities"]},
    {"concept_name": "Length of Stay Tracking", "description": "Calculates visit duration by comparing admission_date and discharge_date from visits table to measure patient flow and bed utilization.", "insight": "Supports operational efficiency queries, identifies prolonged stays, and enables discharge planning optimization.", "keywords": ["length of stay", "visit duration", "patient days"]},
    {"concept_name": "Department Service Volume", "description": "Aggregates visits and procedures by department_id from departments table to compare service line activity and departmental workload.", "insight": "Enables departmental performance analysis, identifies capacity constraints, and supports resource allocation across units.", "keywords": ["department volume", "service line activity", "departmental workload"]},
    {"concept_name": "Prescription Duration Patterns", "description": "Calculates treatment length by comparing start_date and end_date in prescriptions table by medication_id to analyze therapy compliance windows.", "insight": "Supports medication adherence queries, identifies chronic versus acute treatments, and enables refill prediction analysis.", "keywords": ["prescription duration", "treatment length", "medication timeline"]},
    {"concept_name": "Procedure Cost Benchmarking", "description": "Compares cost values across procedure_name in procedures table by provider_id and department to identify pricing variations and efficiency.", "insight": "Enables cost standardization queries, identifies outlier pricing, and supports value-based care negotiations.", "keywords": ["procedure costs", "treatment pricing", "cost variance"]},
    {"concept_name": "Patient Insurance Coverage Mix", "description": "Analyzes insurance_type distribution from patients table to measure payer mix and assess financial risk exposure.", "insight": "Supports payer strategy queries, identifies underserved insurance segments, and guides contracting priorities.", "keywords": ["insurance mix", "payer distribution", "coverage types"]},
    {"concept_name": "Visit Type Utilization", "description": "Tracks visit_type patterns from visits table to compare inpatient, outpatient, and emergency service usage trends.", "insight": "Enables care setting analysis, identifies avoidable emergency visits, and supports care delivery model optimization.", "keywords": ["visit types", "care settings", "service utilization"]},
    {"concept_name": "Provider Experience Impact", "description": "Correlates years_of_experience from providers table with patient outcomes, procedure volumes, and visit complexity metrics.", "insight": "Supports quality analysis queries, identifies mentorship opportunities, and validates experience-based care assignments.", "keywords": ["provider experience", "physician tenure", "experience levels"]},
    {"concept_name": "Claim Processing Timeliness", "description": "Calculates time between visit completion and claim_date in insurance_claims table to measure billing cycle efficiency.", "insight": "Enables revenue cycle speed analysis, identifies claim submission delays, and supports cash flow optimization.", "keywords": ["claim timing", "billing speed", "claim submission"]},
    {"concept_name": "Medication Prescribing Patterns", "description": "Analyzes prescription frequency by medication_id and provider_id from prescriptions table to identify formulary adherence and prescribing variations.", "insight": "Supports clinical variation queries, identifies off-formulary usage, and enables evidence-based prescribing initiatives.", "keywords": ["prescribing patterns", "medication usage", "formulary compliance"]},
    {"concept_name": "Patient Age Demographics", "description": "Calculates patient age distribution from date_of_birth in patients table to segment populations and predict service demand.", "insight": "Enables age-based care planning, identifies pediatric versus geriatric service needs, and supports population health strategies.", "keywords": ["patient age", "age distribution", "demographic profile"]},
    {"concept_name": "Department Location Accessibility", "description": "Maps department_name and location from departments table to analyze service availability and geographic access patterns.", "insight": "Supports facility planning queries, identifies service gaps, and guides expansion or consolidation decisions.", "keywords": ["department location", "service access", "facility distribution"]},
    {"concept_name": "Billing Date Performance", "description": "Tracks billing_date patterns from billing table to measure billing cycle consistency and identify process delays.", "insight": "Enables billing operations analysis, identifies bottlenecks in charge capture, and supports timely revenue recognition.", "keywords": ["billing timing", "charge capture", "billing cycle"]},
    {"concept_name": "Multi-Visit Patient Tracking", "description": "Counts visit frequency by patient_id from visits table to identify high-utilization patients and potential care coordination needs.", "insight": "Supports care management queries, identifies frequent flyers, and enables proactive intervention program targeting.", "keywords": ["frequent patients", "visit frequency", "high utilizers"]},
    {"concept_name": "Diagnosis Code Distribution", "description": "Analyzes diagnosis_code prevalence from diagnoses table to measure disease burden and population health trends.", "insight": "Enables epidemiological queries, identifies common conditions, and supports preventive care program development.", "keywords": ["common diagnoses", "disease prevalence", "diagnosis frequency"]},
    {"concept_name": "Patient Geographic Distribution", "description": "Aggregates patient counts by city and state from patients table to analyze service area coverage and market penetration.", "insight": "Supports market analysis queries, identifies underserved regions, and guides community outreach and access improvement initiatives.", "keywords": ["patient geography", "service area", "regional patients"]},
]


def insert_rules(conn, full_table_name: str, rules: list[dict[str, Any]]) -> None:
    stmt = text(
        f"""
        INSERT INTO {full_table_name}
        (concept_name, description, insight, keywords)
        VALUES (:concept_name, :description, :insight, :keywords)
        """
    )
    conn.execute(stmt, to_rows(rules))


def main():
    load_dotenv()
    engine = get_engine()
    with engine.begin() as conn:
        insert_rules(conn, "finance_schema.finance_business_rules", FINANCE_RULES)
        insert_rules(conn, "retail_schema.retail_business_rules", RETAIL_RULES)
        insert_rules(conn, "healthcare_schema.healthcare_business_rules", HEALTHCARE_RULES)
    print("Inserted 60 business rules across finance, retail, healthcare.")


if __name__ == "__main__":
    main()
