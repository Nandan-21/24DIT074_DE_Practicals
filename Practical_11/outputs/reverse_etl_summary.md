# Practical 11: Data Serving, Reverse ETL, and Security Summary

## 1. Security Architecture Implementation
- **Cryptographic Engine:** Fernet (AES-128-CBC + HMAC-SHA256 Authenticated Encryption)
- **Identity Hashing:** Canonicalized SHA-256 for deterministic multi-system entity resolution
- **Data Masking:** Dynamic partial masking on analyst views (`mask_email`, `mask_name`)
- **Database RBAC:** PostgreSQL Role-Based Access Control enforcing least privilege:
  - `analyst_role`: Allowed `SELECT` ONLY on `view_analyst_customer_metrics`. Base table queries are rejected.
  - `reverse_etl_role`: Granted specific pipeline permissions for reading analytics and updating operational CRM tables.

## 2. Reverse ETL Metrics
| Metric | Value |
|--------|-------|
| **Total Customers Analyzed** | 50 |
| **Eligible for Activation (VIP / Churn)** | 23 |
| **Initial CRM Upserts** | 23 |
| **Subsequent Sync (Idempotency Test)** | 0 inserted, 23 skipped (100% duplicate prevention) |

## 3. Audit Logging
All security events, decryption calls, unauthorized access attempts, and Reverse ETL cycles are recorded with UTC timestamps in `outputs/security_audit_trail.log`.
