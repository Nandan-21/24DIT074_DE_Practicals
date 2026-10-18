# Practical 9: Data Modeling for Analytics - Validation Report

## 1. Dimensional Architecture Overview
- **Modeling Paradigm:** Kimball Dimensional Modeling (Star Schema)
- **Central Fact Table:** `fact_sales`
- **Fact Grain:** Exactly **one row per product line item** within a customer order
- **Dimensions:** `dim_date`, `dim_customer` (SCD Type 2), `dim_product`, `dim_store`

## 2. Slowly Changing Dimension (SCD Type 2) Implementation
- **Total Customer Surrogate Records:** 16
- **Current Active Customer Records (`is_current = TRUE`):** 8
- **Historical Superseded Records (`is_current = FALSE`):** 8
- **Historical Fact Integrity:** Historical orders prior to 2025-07-01 accurately resolve to the customer's prior address, preserving historical analytical accuracy.

## 3. Star Schema vs Snowflake Schema Comparison (Supplementary Problem)
| Dimension Feature | Kimball Star Schema | Normalized Snowflake Schema |
|-------------------|---------------------|-----------------------------|
| **Total Dimension Tables** | 4 | 7 |
| **Hierarchy Storage** | Denormalized in `dim_product`, `dim_store` | Normalized into `dim_category`, `dim_subcategory`, `dim_region` |
| **Required Joins (Category/Region Report)** | 2 Joins | 5 Joins |
| **Average Query Latency (10 runs)** | **2.934 ms** | **4.049 ms** |
| **Analysis** | Simpler SQL queries, faster aggregations, optimal for BI tools | Eliminates redundant text storage at cost of extra join overhead |
