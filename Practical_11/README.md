# Practical 11: Data Serving, Reverse ETL, and Security

## 1. Title and Objective
**Title:** Secure Analytical Data Serving, Cryptographic Column Protection, Database RBAC, and Operational Reverse ETL  
**Course Code:** ITUC301 – Data Engineering  
**Objective:** Create a hardened analytical serving platform that securely shares enriched customer insights with downstream users while enforcing robust data privacy controls. The architecture implements column-level authenticated encryption (Fernet), deterministic canonicalized SHA-256 identity hashing, dynamic data masking, database Role-Based Access Controls (RBAC), and an automated, idempotent Reverse ETL synchronization pipeline that activates high-value and at-risk customer segments back into operational customer relationship management (CRM) tools.

---

## 2. Tools and Technologies Used
- **PostgreSQL 16 (Docker Container):** Database engine with SQL views, user roles, and fine-grained relational privileges.
- **Python Cryptography (`cryptography.fernet`):** Authenticated symmetric encryption (AES-128 in CBC mode with HMAC-SHA256).
- **Python `hashlib`:** Cryptographic SHA-256 identity hashing with canonicalization.
- **Reverse ETL Engine:** Custom Python synchronization worker executing state-tracking idempotent upserts.
- **Centralized Audit Logging:** Structured JSON audit engine logging actor roles, access attempts, and sync cycles.
- **Pytest:** Automated test suite validating cryptographic roundtrips, privilege denial, and sync idempotency.

---

## 3. Security Architecture & Data Flow

```
+-------------------------------------------------------------------------------------------------+
|                                 Raw Customer Analytics Dataset                                  |
+-------------------------------------------------------------------------------------------------+
                                                |
                 +------------------------------+------------------------------+
                 |                                                             |
                 v                                                             v
       [Deterministic Hashing]                                       [Authenticated Encryption]
       SHA-256 (Canonicalized)                                       Fernet (AES-128-CBC + HMAC)
                 |                                                             |
                 +------------------------------+------------------------------+
                                                |
                                                v
                       +------------------------------------------------+
                       |           customer_analytics_secure            |
                       | (email_hash, encrypted_email, masked_email,    |
                       |  segment, ltv_score, churn_risk_score)         |
                       +------------------------------------------------+
                                       |                |
             (GRANT SELECT to analyst) |                | (GRANT to reverse_etl_role)
                                       v                v
          +---------------------------------+     +---------------------------------+
          |  view_analyst_customer_metrics  |     |        Reverse ETL Engine       |
          |  (Masked Name, Masked Email,    |     |    (Extracts At-Risk / VIPs,    |
          |   No Plaintext/Ciphertext)      |     |     Applies Activation Tags)    |
          +---------------------------------+     +---------------------------------+
                         |                                          |
                         v                                          v
                 [Data Analyst User]                     [crm_customer_profiles]
              (Direct access to base table              (Operational CRM Target -
               strictly BLOCKED by RBAC)                 Salesforce / HubSpot Sync)
```

### Definitions: Hashing vs Tokenization vs Masking vs Encryption
- **Deterministic Hashing (SHA-256):** One-way mathematical transformation. Cannot be reversed. Used for cross-system identity matching and deduplication without revealing the underlying raw identity string.
- **Authenticated Encryption (Fernet):** Two-way reversible transformation using a secret cryptographic key. Protects sensitive data at rest; only authorized services with the key can decrypt to plaintext.
- **Dynamic Data Masking:** Presentation-layer obfuscation (e.g., `a***h@domain.com`). Prevents shoulder surfing and minimizes exposure to internal analysts without breaking data structure.
- **Tokenization:** Replacing sensitive values with non-mathematical random surrogate tokens mapped via a secure vault.

---

## 4. Directory Structure
```
Practical_11/
├── outputs/
│   ├── analyst_masked_sample.json       # Sample records visible to analyst_role
│   ├── reverse_etl_summary.md           # Summary of Reverse ETL synchronization
│   ├── reverse_etl_sync_results.json    # Sync metrics and idempotency counts
│   ├── secret.key                       # Securely generated Fernet encryption key
│   └── security_audit_trail.log         # Structured JSON audit log
├── sql/
│   ├── 01_analytical_serving_schema.sql # Base secure table, state ledger, and views
│   ├── 02_operational_crm_schema.sql    # Target operational CRM profiles table
│   └── 03_rbac_roles_and_grants.sql     # PostgreSQL role definitions and permissions
├── src/
│   ├── crypto_utils.py                  # SHA-256 hashing, Fernet encryption, and masking
│   ├── data_generator.py                # Synthetic customer analytics generator
│   ├── db_service.py                    # Multi-role database connection service
│   ├── reverse_etl_engine.py            # Operational synchronization engine
│   └── security_audit_logger.py         # Structured JSON audit logging
├── tests/
│   └── test_security_and_sync.py        # Automated test suite
├── .env.example                         # Environment configuration template
├── requirements.txt                     # Dependencies
├── main.py                              # End-to-end execution script
└── README.md                            # Complete documentation
```

---

## 5. Execution Instructions

### A. Environment Setup & Container Verification
Ensure the PostgreSQL container from Practical 7 is running:
```powershell
docker compose -f Practical_7\docker-compose.yml up -d
```

Install requirements:
```powershell
.\venv\Scripts\Activate.ps1
pip install -r Practical_11\requirements.txt
```

### B. Run Complete Security & Reverse ETL Pipeline
```powershell
python Practical_11\main.py
```

### C. Run Automated Tests
```powershell
pytest Practical_11\tests\ -v
```

---

## 6. Answers to Key Evaluation Questions

### Question 1: Why do organizations deploy Reverse ETL workflows to sync analytical insights back to production tools instead of having production apps query warehouses directly?
1. **OLTP vs OLAP Architectural Mismatch:** Analytical data warehouses (Snowflake, BigQuery, DuckDB) are optimized for large sequential scans and bulk aggregations, not high-concurrency low-latency single-row key lookups (sub-10ms) required by operational production applications.
2. **Operational Tool Native Integration:** Business teams work daily inside Salesforce, HubSpot, Zendesk, and Marketo. Reverse ETL pushes high-value segments and churn scores directly into the business tools where operational staff execute workflows, rather than requiring non-technical teams to write SQL against a data warehouse.
3. **Connection Spikes & Rate Limiting:** Exposing a data warehouse to thousands of concurrent production API calls causes connection exhaustion, unpredictable queueing delays, and exorbitant compute credit consumption.
4. **Resilience & Decoupling:** Reverse ETL buffers updates asynchronously. If the data warehouse is paused for maintenance or undergoing intensive nightly ELT processing, operational production apps continue uninterrupted.

---

### Question 2: How do column-level hashing and tokenization techniques help an enterprise meet strict privacy data regulations like GDPR or CCPA?
- **Data Minimization (GDPR Article 5):** Analysts only require attributes like `segment` and `churn_risk`. Exposing raw emails or names violates the principle that personal data must be limited to what is strictly necessary.
- **Pseudonymization (GDPR Article 32 & Recital 26):** Hashing or encrypting personal identifiers separates identity from behavioral records. If an analytical database backup is breached, the attacker cannot identify real humans without access to the separately guarded encryption key or salt.
- **Right to Erasure / Forgotten (GDPR Article 17):** With Crypto-Shredding, if a customer requests account deletion, destroying their individual encryption key instantly renders all historical records undecipherable without executing complex multi-terabyte deletion cascades across append-only data lakes.
- **Important Note:** A deterministic unsalted hash is still legally considered **pseudonymous data** under GDPR (not anonymous), because it can be re-identified through rainbow tables or frequency analysis.

---

### Question 3: Detail the architectural differences between exposing data to analytical clients via direct views, data virtualization layers, and pre-computed data marts.
- **Direct Database Views (`CREATE VIEW ...`):**
  - **Mechanics:** Executes the underlying SQL query against base tables on-demand whenever the view is queried.
  - **Pros:** Zero additional storage required; always yields up-to-the-second live data; easy to implement.
  - **Cons:** Incurs full computational cost on every query invocation; no physical decoupling or cross-engine federation.
- **Data Virtualization Layers (e.g., Dremio, Denodo, Trino):**
  - **Mechanics:** An abstraction layer that queries multiple disparate data engines (PostgreSQL, MinIO S3, Snowflake, MongoDB) on the fly, presenting a single virtual SQL endpoint.
  - **Pros:** Eliminates physical data duplication; enables unified cross-source federated queries without ELT.
  - **Cons:** Network latency across distributed sources; unpredictable query execution times.
- **Pre-computed Data Marts (e.g., Aggregated Star Schema Marts):**
  - **Mechanics:** Physical tables periodically loaded with pre-calculated, materialized KPIs.
  - **Pros:** Sub-millisecond dashboard query speeds; shields production databases from analytical traffic.
  - **Cons:** Data is as fresh as the last batch refresh; consumes physical storage.

---

## 7. Supplementary Problem Implementation
**Requirement:** Implement a database access control layer that restricts data views so that members of a simulated data analyst role can only see masked or tokenized versions of sensitive customer identity columns.

**Implementation Details:**
- Implemented in `sql/01_analytical_serving_schema.sql` and `sql/03_rbac_roles_and_grants.sql`.
- **Restricted View Definition:**
  ```sql
  CREATE VIEW view_analyst_customer_metrics AS
  SELECT customer_id, email_hash, masked_email, masked_name, segment, ltv_score, churn_risk_score, total_orders, last_active_date
  FROM customer_analytics_secure;
  ```
- **RBAC Grants:**
  - `GRANT SELECT ON view_analyst_customer_metrics TO analyst_role;`
  - `REVOKE ALL ON customer_analytics_secure FROM analyst_role;`
- **Verification:** When `analyst_role` queries `view_analyst_customer_metrics`, it sees masked identifiers (`a***h@domain.com`). When it attempts `SELECT * FROM customer_analytics_secure`, PostgreSQL raises:
  `ERROR: permission denied for table customer_analytics_secure`.
- Tested and verified in `tests/test_security_and_sync.py`.
