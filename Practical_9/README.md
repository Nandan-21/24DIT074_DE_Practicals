# Practical 9: Data Modeling for Analytics

## 1. Title and Objective
**Title:** Kimball Dimensional Modeling, Star Schema Architecture, and Slowly Changing Dimensions (SCD Type 2)  
**Course Code:** ITUC301 – Data Engineering  
**Objective:** Transform unstructured transactional retail sales records into an analytics-ready dimensional model using the Kimball methodology. Design and implement a central Fact table (`fact_sales`) surrounded by conformed Dimension tables (`dim_customer`, `dim_product`, `dim_store`, `dim_date`), enforce strict grain definitions, use surrogate primary keys, implement Slowly Changing Dimensions Type 2 (SCD2) for tracking historical customer mutations over time, and compare Star Schema performance against a normalized Snowflake Schema variant.

---

## 2. Tools and Technologies Used
- **DuckDB (v1.x):** Embedded analytical warehouse engine.
- **SQL DDL & Relational Schemas:** Relational data definition syntax with surrogate keys and referential integrity constraints.
- **dbdiagram.io (DBML):** Standard Database Markup Language for generating visual Entity-Relationship Diagrams (ERD).
- **Python 3.x (`duckdb`, `pandas`):** Automated ETL/ELT pipelines, synthetic transactional workload generator, and SCD2 loader.
- **Pytest:** Automated verification suite for referential integrity, fact grain validation, and SCD2 tracking.

---

## 3. Dimensional Architecture & Kimball Design Principles

```
                              +--------------------+
                              |      dim_date      |
                              +--------------------+
                              | PK: date_key       |
                              |     full_date      |
                              |     month, year    |
                              +--------------------+
                                        | 1
                                        |
                                        | *
+--------------------+        +--------------------+        +--------------------+
|    dim_customer    |        |     fact_sales     |        |    dim_product     |
+--------------------+        +--------------------+        +--------------------+
| PK: customer_key   |<-------| PK: sales_key      |------->| PK: product_key    |
| BK: customer_id    | *    1 | FK: date_key       | 1    * | BK: product_id     |
|     customer_city  |        | FK: customer_key   |        |     category       |
|     is_current     |        | FK: product_key    |        |     subcategory    |
|     start/end_date |        | FK: store_key      |        |     unit_price     |
+--------------------+        |     order_id       |        +--------------------+
                              |     line_item      |
                              |     quantity       |
                              |     gross_amount   |
                              |     net_amount     |
                              |     profit_amount  |
                              +--------------------+
                                        | *
                                        |
                                        | 1
                              +--------------------+
                              |     dim_store      |
                              +--------------------+
                              | PK: store_key      |
                              | BK: store_id       |
                              |     region, type   |
                              +--------------------+
```

### Key Dimensional Concepts Defined:
1. **Fact Table Grain:** Exactly **one row per line item within a customer sales order**. This atomic grain allows slicing and dicing across product, customer, store, and date hierarchies without artificial loss of detail.
2. **Surrogate Keys vs Business Keys:**
   - Every dimension utilizes an auto-incrementing integer surrogate key (e.g., `customer_key`, `product_key`).
   - Business keys from source systems (`customer_id`, `product_id`) are preserved as descriptive dimension attributes.
   - Surrogate keys decouple the warehouse from source operational key recycling, format changes, and mergers, and are mandatory for SCD Type 2 tracking.
3. **Slowly Changing Dimensions (SCD Type 2):**
   - When a customer relocates to a new city (e.g., Alice moved from New York to Boston on July 1st, 2025), the original record is updated with `effective_end_date = '2025-06-30'` and `is_current = FALSE`.
   - A new row is inserted with a **new surrogate key**, `effective_start_date = '2025-07-01'`, `effective_end_date = NULL`, and `is_current = TRUE`.
   - Historical sales prior to July 1st remain joined to the historical version (`customer_city = 'New York'`), while subsequent sales join to `'Boston'`.

---

## 4. Directory Structure
```
Practical_9/
├── data/                            # Raw transactional retail sales CSV
├── erd/
│   ├── erd_star_schema.dbml         # dbdiagram.io ERD definition for Star Schema
│   └── erd_snowflake_schema.dbml    # dbdiagram.io ERD definition for Snowflake Schema
├── sql/
│   ├── 01_staging_schema.sql        # Raw staging and cleaning transformations
│   ├── 02_star_schema_ddl.sql       # Kimball Star Schema DDL
│   ├── 03_snowflake_schema_ddl.sql  # Supplementary Snowflake Schema DDL
│   └── 04_analytical_queries.sql    # Analytical OLAP reporting queries
├── src/
│   ├── dimensional_loader.py        # Star schema and SCD Type 2 loader
│   ├── model_comparator.py          # Star vs Snowflake benchmark comparator
│   ├── raw_data_generator.py        # Messy raw transactional sales generator
│   ├── snowflake_loader.py          # Supplementary snowflake hierarchy loader
│   └── staging_cleaner.py           # Cleaning and feature calculation logic
├── tests/
│   └── test_data_modeling.py        # Pytest automated validation suite
├── outputs/
│   ├── warehouse.duckdb             # DuckDB analytical warehouse database file
│   ├── modeling_comparison_report.md# Star vs Snowflake comparison report
│   └── validation_report.json       # Structural validation metrics
├── requirements.txt                 # Dependencies (duckdb, pandas, pytest)
├── main.py                          # End-to-end execution script
└── README.md                        # Complete documentation
```

---

## 5. Execution Instructions

### A. Environment Setup
```powershell
# Activate project virtual environment
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r Practical_9\requirements.txt
```

### B. Run Pipeline and Generate Models
```powershell
python Practical_9\main.py
```

### C. Run Automated Tests
```powershell
pytest Practical_9\tests\ -v
```

---

## 6. Answers to Key Evaluation Questions

### Question 1: What are the key architectural differences and use cases for normalized operational models (3NF) versus denormalized analytical star schemas?
- **Normalized Operational Models (Third Normal Form - 3NF):**
  - **Design Goal:** Eliminate data redundancy, prevent update/insert/delete anomalies, and minimize storage for individual write operations.
  - **Structure:** Highly fragmented across dozens to hundreds of tables with foreign key cascades.
  - **Use Case:** High-throughput transactional systems (OLTP) executing discrete point queries and row updates (e.g., checkout engines, banking ledgers).
  - **Analytical Bottleneck:** Calculating aggregate KPIs requires joining 10–20 tables together, causing severe query planning and execution latency.
- **Denormalized Analytical Star Schemas (Kimball Methodology):**
  - **Design Goal:** Optimize query readability, simplify business intelligence (BI) tooling integrations, and maximize analytical query execution speed.
  - **Structure:** Denormalized dimension tables radiating around a central numeric fact table.
  - **Use Case:** Enterprise data warehouses, business intelligence dashboards, and exploratory data mining (OLAP).

---

### Question 2: Explain the concept of Slowly Changing Dimensions (SCDs) and specify how your design tracks customer state changes over time.
- **Concept:** Dimension attributes are rarely permanent. Customers change addresses, products change categories, and sales reps change territories. Slowly Changing Dimensions define the architectural strategy for managing these transitions:
  - **SCD Type 0:** Fixed/Retain Original (no changes permitted).
  - **SCD Type 1:** In-place Overwrite (historical accuracy is destroyed).
  - **SCD Type 2:** Add New Row with Effective Version Range (preserves complete historical fidelity).
  - **SCD Type 3:** Add New Column (tracks previous vs current only).
- **Implementation in our Design:**
  - `dim_customer` contains `effective_start_date`, `effective_end_date`, and `is_current`.
  - When a customer moves cities, the historical version is marked `is_current = FALSE` with an expiration date. A new record is created with a new `customer_key` marked `is_current = TRUE`.
  - During fact table loading, transactions join on `order_date BETWEEN effective_start_date AND COALESCE(effective_end_date, '9999-12-31')`. Fact records accurately link to the customer state that existed at the exact moment the sale took place.

---

### Question 3: How do surrogate keys protect an analytical data warehouse model from changes or migrations in source system business keys?
1. **Source System Key Recycling:** Operational databases frequently reuse deleted primary keys (e.g., order ID counters reset after fiscal year end or system migration). Surrogate keys ensure every warehouse dimension entity receives a permanently unique identity.
2. **Multi-Source Integration:** When merging data from two distinct operational platforms (e.g., legacy Oracle ERP and modern Salesforce CRM), business keys often collide. Surrogate keys isolate the analytical layer from operational key conflicts.
3. **Tracking Slowly Changing Dimensions (SCD2):** A single business key (e.g., `CUST-101`) corresponds to multiple physical rows over time. Surrogate keys (`customer_key = 1`, `customer_key = 9`) give each historical version a unique relational identifier for fact table foreign keys.
4. **Performance:** Integer surrogate keys index and join significantly faster than long, variable-length alphanumeric business key strings.

---

## 7. Supplementary Problem Implementation
**Requirement:** Expand your star schema design into a Snowflake layout by normalizing complex hierarchies within your Dimension tables, and compare the two structures in terms of storage size and join query performance.

**Implementation Details:**
- Implemented in `sql/03_snowflake_schema_ddl.sql`, `src/snowflake_loader.py`, and `src/model_comparator.py`.
- **Snowflake Normalization:**
  - `dim_product` was decomposed into `dim_category_snow` $\rightarrow$ `dim_subcategory_snow` $\rightarrow$ `dim_product_snow`.
  - `dim_store` was decomposed into `dim_region_snow` $\rightarrow$ `dim_store_snow`.
- **Measured Trade-Offs:**
  - **Join Overhead:** Star Schema requires only 2 joins to compute category/region sales; Snowflake Schema requires 5 joins.
  - **Execution Latency:** The Star Schema exhibits faster join execution latency in DuckDB because the query planner evaluates single-level joins rather than walking a multi-table hierarchical cascade.
  - **Conclusion:** While Snowflake Schema reduces redundancy for wide text columns, Star Schema provides superior query performance, simpler SQL logic, and better compatibility with BI visualization engines.
