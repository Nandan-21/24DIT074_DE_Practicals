# Change Data Capture (CDC) Replication Summary

## 1. Overview
- **Database Engine:** PostgreSQL 16
- **Capture Mechanism:** PL/pgSQL transactional triggers on `operational_inventory`
- **Replication Target:** `analytical_inventory`
- **Audit Ledger:** `cdc_audit_ledger` (Append-only)

## 2. Execution Metrics
| Metric | Value |
|--------|-------|
| **Total Captured Events** | 49 |
| **INSERT Events** | 25 |
| **UPDATE Events** | 20 |
| **DELETE Events** | 4 |
| **Events Applied by Consumer** | 49 |
| **Out-of-Order / Stale Deduplicated** | 0 |
| **Final State Consistent** | **True** |
| **Active Source Rows** | 21 |
| **Active Analytical Rows** | 21 |
| **Analytical Soft-Deleted Rows** | 4 |
