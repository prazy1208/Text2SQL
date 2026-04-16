-- Insert business rules for all schemas

-- ============================================
-- HEALTHCARE BUSINESS RULES
-- ============================================
INSERT INTO healthcare_schema.healthcare_business_rules
(concept_name, description, insight, keywords)
VALUES
('Patient Registration Activity',
'Patient registration activity reflects how new patients begin interacting with healthcare services.',
'Monitoring registration patterns helps healthcare providers understand patient intake trends and service demand.',
ARRAY['new patients','patient registration','patient intake','patient enrollment']),

('Patient Demographic Distribution',
'Patient demographic distribution describes how patients are represented across different demographic characteristics.',
'Understanding demographic distribution helps healthcare organizations identify the populations they serve.',
ARRAY['patient demographics','patient distribution','demographic analysis']),

('Patient Visit Activity',
'Patient visit activity represents how frequently patients interact with healthcare providers through appointments or consultations.',
'Tracking visit activity helps healthcare providers understand service utilization patterns.',
ARRAY['patient visits','appointments','consultations','visit frequency']),

('Healthcare Service Utilization',
'Healthcare service utilization reflects how healthcare services are used by patients across the organization.',
'Analyzing service utilization helps identify which services are most frequently accessed.',
ARRAY['service usage','healthcare utilization','medical services']),

('Treatment Patterns',
'Treatment patterns describe how different treatments or medical procedures are provided to patients.',
'Understanding treatment patterns helps healthcare organizations evaluate care delivery practices.',
ARRAY['treatment patterns','medical procedures','patient treatment']),

('Patient Care Activity',
'Patient care activity reflects the range of interactions between healthcare providers and patients during care delivery.',
'Monitoring care activity helps organizations understand healthcare workload and service delivery levels.',
ARRAY['patient care','care activity','medical care interactions']),

('Patient Health Trends',
'Patient health trends describe how patient-related health activities evolve over time.',
'Tracking trends helps healthcare providers understand changes in care demand and treatment needs.',
ARRAY['health trends','patient health patterns','health activity trends']),

('Healthcare Provider Activity',
'Healthcare provider activity reflects the level of engagement healthcare professionals have in delivering patient care.',
'Analyzing provider activity helps healthcare organizations understand workload distribution and service capacity.',
ARRAY['provider activity','medical staff activity','clinical workload']),

('Appointment Patterns',
'Appointment patterns describe how patients schedule and attend healthcare visits over time.',
'Understanding appointment patterns helps healthcare providers optimize scheduling and service availability.',
ARRAY['appointments','visit scheduling','appointment trends']),

('Patient Engagement',
'Patient engagement reflects how actively patients participate in healthcare services and interactions.',
'High levels of engagement often indicate stronger patient involvement in care processes.',
ARRAY['patient engagement','patient interaction','healthcare participation']),

('Healthcare Activity Trends',
'Healthcare activity trends describe how healthcare interactions and service usage change across different time periods.',
'Trend analysis helps healthcare organizations anticipate demand and allocate resources effectively.',
ARRAY['healthcare trends','medical activity trends','service demand trends']),

('Patient Participation',
'Patient participation reflects how widely healthcare services are utilized across the patient population.',
'Analyzing participation helps healthcare providers understand overall service reach.',
ARRAY['patient participation','service adoption','patient involvement']),

('Clinical Activity Monitoring',
'Clinical activity monitoring focuses on observing patterns in healthcare delivery and patient interactions.',
'Monitoring clinical activity helps healthcare organizations maintain efficient service operations.',
ARRAY['clinical activity','medical operations','care monitoring']),

('Patient Service Demand',
'Patient service demand reflects the level of need for healthcare services among patients.',
'Understanding demand helps healthcare providers plan staffing, services, and resources.',
ARRAY['service demand','healthcare demand','medical demand']),

('Healthcare Interaction Distribution',
'Healthcare interaction distribution describes how patient interactions are spread across different services or providers.',
'Analyzing interaction distribution helps healthcare organizations understand how care is delivered.',
ARRAY['healthcare interactions','patient interactions','service distribution']);

-- ============================================
-- RETAIL BUSINESS RULES
-- ============================================
INSERT INTO retail_schema.retail_business_rules
(concept_name, description, insight, keywords)
VALUES
('Customer Acquisition',
'Customer acquisition refers to the process of gaining new customers who begin interacting with the business.',
'Tracking acquisition helps businesses understand growth and evaluate outreach or marketing efforts.',
ARRAY['new customers','customer growth','customer signup','customer acquisition']),

('Customer Base Distribution',
'Customer base distribution describes how customers are spread across different geographic locations.',
'Understanding where customers are concentrated helps businesses identify strong markets and areas for expansion.',
ARRAY['customer location','customer regions','geographic distribution','customers by region']),

('Customer Growth Trends',
'Customer growth trends represent how the number of customers changes over time.',
'Analyzing these trends helps businesses measure long-term growth and customer adoption.',
ARRAY['customer trends','customer increase','customer growth over time']),

('Customer Engagement',
'Customer engagement reflects how actively customers interact with the business through purchasing behavior.',
'Understanding engagement levels helps identify loyal customers and overall customer activity.',
ARRAY['customer engagement','customer activity','active customers']),

('Customer Purchase Behavior',
'Customer purchase behavior describes patterns in how customers buy products over time.',
'Studying purchasing patterns helps businesses understand customer preferences and buying habits.',
ARRAY['purchase behavior','customer buying patterns','shopping behavior']),

('Product Catalog Overview',
'Product catalog analysis focuses on understanding the variety and organization of products offered by a business.',
'Reviewing the product catalog helps businesses maintain balanced offerings across categories and brands.',
ARRAY['product catalog','product list','available products']),

('Product Category Analysis',
'Product categories group similar products together to simplify product organization and analysis.',
'Analyzing categories helps businesses understand demand patterns across different product types.',
ARRAY['product category','product categories','category analysis']),

('Brand Representation',
'Brand representation reflects how different brands appear within the product assortment.',
'Understanding brand presence helps businesses evaluate brand diversity and popularity.',
ARRAY['brand presence','brand distribution','brand representation']),

('Product Popularity',
'Product popularity reflects the level of interest customers show in particular products.',
'Popularity insights help businesses identify products that consistently attract customer attention.',
ARRAY['popular products','trending products','product interest']),

('Product Introduction Trends',
'Product introduction trends describe how frequently new products are added to the catalog.',
'Monitoring product introductions helps businesses understand innovation and catalog expansion.',
ARRAY['new products','product launch','recent products']),

('Sales Activity',
'Sales activity represents the overall purchasing interactions occurring between customers and the business.',
'Monitoring activity levels helps businesses evaluate demand and operational performance.',
ARRAY['sales activity','transactions','purchase activity']),

('Order Volume',
'Order volume reflects the number of purchasing transactions occurring within a given timeframe.',
'Tracking order volume helps businesses understand changes in purchasing frequency.',
ARRAY['order volume','transaction count','number of purchases']),

('Sales Trends',
'Sales trends describe how purchasing activity evolves across different time periods.',
'Trend analysis helps identify growth patterns and seasonal behavior.',
ARRAY['sales trends','purchase trends','transaction trends']),

('Customer Purchasing Distribution',
'Customer purchasing distribution describes how purchasing activity varies among different customers.',
'Understanding purchasing distribution helps identify customers with higher engagement levels.',
ARRAY['customer spending','top customers','customer purchase activity']),

('Product Demand Patterns',
'Product demand patterns describe how frequently different products attract customer purchases.',
'Understanding demand patterns helps businesses recognize products that drive consistent interest.',
ARRAY['product demand','high demand products','frequently purchased products']),

('Product Category Demand',
'Category demand analysis evaluates how customer interest varies across different product categories.',
'This analysis helps businesses determine which types of products attract the most attention.',
ARRAY['category demand','popular categories','category interest']),

('Brand Interest',
'Brand interest reflects the level of customer attention or engagement associated with particular brands.',
'Analyzing brand interest helps businesses understand which brands resonate most with customers.',
ARRAY['brand interest','popular brands','brand popularity']),

('Customer Activity Over Time',
'Customer activity over time measures how purchasing engagement changes across different time periods.',
'Observing activity patterns helps identify periods of high or low customer interaction.',
ARRAY['customer activity trends','shopping activity','purchase timing']);

-- ============================================
-- FINANCE BUSINESS RULES
-- ============================================
INSERT INTO finance_schema.finance_business_rules
(concept_name, description, insight, keywords)
VALUES
('Transaction Activity',
'Transaction activity represents the overall movement of financial operations occurring within a system.',
'Monitoring transaction activity helps organizations understand operational intensity and financial usage patterns.',
ARRAY['transactions','transaction activity','financial activity']),

('Transaction Volume Trends',
'Transaction volume trends describe how the number of financial transactions changes over time.',
'Analyzing transaction volume helps identify periods of increased financial activity or operational demand.',
ARRAY['transaction trends','transaction volume','transaction increase']),

('Account Activity',
'Account activity reflects how actively financial accounts are used for transactions or operations.',
'Understanding account activity helps identify frequently used accounts and engagement patterns.',
ARRAY['account activity','active accounts','account usage']),

('Account Distribution',
'Account distribution describes how accounts are organized or spread across different categories or groups.',
'Analyzing distribution helps organizations understand structural patterns within the financial system.',
ARRAY['account distribution','account categories','account groups']),

('Financial Flow Analysis',
'Financial flow analysis examines how value moves across the financial system through transactions.',
'Understanding flow patterns helps identify major channels of financial movement.',
ARRAY['financial flow','money movement','transaction flow']),

('Spending Patterns',
'Spending patterns describe how financial resources are utilized across various activities.',
'Analyzing spending behavior helps organizations identify common expenditure trends.',
ARRAY['spending patterns','financial spending','expense behavior']),

('Revenue Activity',
'Revenue activity represents financial inflows generated through operational or business activities.',
'Monitoring revenue activity helps organizations track financial performance over time.',
ARRAY['revenue activity','income generation','financial inflow']),

('Expense Activity',
'Expense activity reflects financial outflows resulting from operational or business expenditures.',
'Tracking expense patterns helps organizations understand cost distribution and spending behavior.',
ARRAY['expenses','cost activity','financial outflow']),

('Financial Balance Monitoring',
'Balance monitoring focuses on tracking the financial position of accounts or entities over time.',
'Understanding balance patterns helps identify financial stability and resource availability.',
ARRAY['balance monitoring','account balances','financial position']),

('Customer Financial Behavior',
'Customer financial behavior reflects how customers interact with financial services or perform financial operations.',
'Studying financial behavior helps organizations understand customer engagement with financial systems.',
ARRAY['financial behavior','customer transactions','customer financial activity']),

('Transaction Frequency',
'Transaction frequency measures how often financial operations occur within a defined period.',
'Monitoring frequency helps organizations detect changes in system usage patterns.',
ARRAY['transaction frequency','transaction rate','financial operations']),

('Financial Activity Distribution',
'Financial activity distribution describes how financial operations are spread across different entities or accounts.',
'Understanding distribution helps identify concentration of financial activity.',
ARRAY['financial distribution','activity spread','transaction concentration']),

('Financial Trends Over Time',
'Financial trends describe how financial activity evolves across different time periods.',
'Trend analysis helps organizations identify growth patterns and financial cycles.',
ARRAY['financial trends','transaction trends','activity trends']),

('High Activity Entities',
'High activity entities represent accounts or participants that show elevated levels of financial operations.',
'Identifying high activity entities helps organizations monitor major contributors to financial activity.',
ARRAY['high activity accounts','active entities','frequent transactions']),

('Financial Participation',
'Financial participation reflects how widely financial services or operations are used among participants.',
'Analyzing participation helps understand adoption and engagement levels.',
ARRAY['financial participation','system usage','participant activity']),

('Financial Growth Patterns',
'Financial growth patterns describe increases or decreases in financial activity levels over time.',
'Understanding growth patterns helps organizations assess expansion or contraction in operations.',
ARRAY['financial growth','activity growth','transaction growth']),

('Operational Financial Insights',
'Operational financial insights focus on understanding the behavior and structure of financial operations within a system.',
'These insights help organizations make informed decisions about financial management and operational efficiency.',
ARRAY['financial insights','operational finance','financial analytics']);
