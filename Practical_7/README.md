# Practical 7: Change Data Capture (CDC)

## 1. Title and Objective
**Title:** Incremental Change Data Capture (CDC) Simulation and Replication Engine  
**Course Code:** ITUC301 – Data Engineering  
**Objective:** Simulate an incremental Change Data Capture (CDC) loop to safely track and capture all row mutations (`INSERT`, `UPDATE`, `DELETE`) occurring on an operational PostgreSQL transaction system. These operational row changes are streamed into an append-only audit ledger via transactional PL/pgSQL triggers and safely replayed onto an analytical table to maintain continuous data consistency without requiring destructive full-table database dumps.

---

## 2. Tools and Technologies Used
- **PostgreSQL 16 (Docker Container):** Relational operational and analytical database.
- **PL/pgSQL Triggers:** Transactional event-capture triggers ensuring ACID guarantees for CDC events.
- **Python 3.x (`psycopg2-binary`):** Incremental CDC replication consumer and transaction generator.
- **Docker Compose:** Container orchestration for local database provisioning.
- **JSONB Data Types:** Schema-flexible storage of pre-mutation (`old_row`) and post-mutation (`new_row`) snapshots.
- **Pytest:** Automated test suite verifying trigger capture, transaction rollback isolation, and out-of-order deduplication.

---

## 3. Architecture and Data Flow

```
+-----------------------------------------------------------------------------------------+
|                              Operational Transaction (OLTP)                             |
|                           Table: operational_inventory                                  |
+-----------------------------------------------------------------------------------------+
                    |                                           |
         (BEFORE UPDATE: Increment version)                     | (AFTER INSERT/UPDATE/DELETE)
                    |                                           |
                    v                                           v
       [trg_bump_version (PL/pgSQL)]              [trg_capture_cdc (PL/pgSQL)]
                                                                |
                                                                v
                                                 +------------------------------+
                                                 |       cdc_audit_ledger       |
                                                 |  (Append-Only Event Store)   |
                                                 +------------------------------+
                                                                |
                                                    (SELECT ... FOR UPDATE)
                                                                |
                                                                v
                                                    +-----------------------+
                                                    |  Python CDC Consumer  |
                                                    | (Version Ordering &   |
                                                    |  Deduplication Check) |
                                                    +-----------------------+
                                                                |
                                                       (Atomic Upsert / Delete)
                                                                |
                                                                v
                                                 +------------------------------+
                                                 |     analytical_inventory     |
                                                 |      (OLAP Sync Replica)     |
                                                 +------------------------------+
```

### ACID Guarantees & Transaction Isolation:
- Because the capture trigger executes inside the user's transaction boundary, if an operational transaction fails or rolls back, its CDC audit record rolls back with it. No "phantom" mutations are ever logged.
- The Python CDC consumer processes changes in transaction blocks, marking the ledger event `is_processed = TRUE` within the same transaction that updates the analytical table.

---

## 4. Directory Structure
```
Practical_7/
├── docker-compose.yml               # PostgreSQL 16 container definition
├── .env.example                     # Database credentials template
├── requirements.txt                 # Python dependencies (psycopg2-binary, pytest)
├── sql/
│   └── 01_init_cdc_schema.sql       # DDL for operational, audit, replica tables & triggers
├── src/
│   ├── cdc_consumer.py              # Incremental consumer with deduplication
│   ├── db_connection.py             # Resilient connection manager
│   ├── transaction_generator.py     # Live inventory transaction simulator
│   └── verifier.py                  # Consistency verification between OLTP & OLAP
├── tests/
│   └── test_cdc.py                  # Automated validation test suite
├── outputs/
│   ├── cdc_execution_summary.md     # Run statistics and operational counts
│   └── consistency_report.json      # Column-by-column verification results
├── main.py                          # End-to-end execution script
└── README.md                        # Complete documentation
```

---

## 5. Prerequisites & Execution Instructions

### A. Start PostgreSQL Service
```powershell
# From Practical_7 directory
cd Practical_7
docker compose up -d
```
Wait ~5 seconds for the database healthcheck to report healthy.

### B. Install Python Dependencies
```powershell
# Activate project virtual environment
..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### C. Run CDC Pipeline Demonstration
```powershell
python main.py
```

### D. Run Automated Tests
```powershell
pytest tests/ -v
```

---

## 6. Answers to Key Evaluation Questions

### Question 1: Contrast the background resource footprint of log-based change data capture mechanisms against classic query-based scheduling checks on production tables.
- **Query-Based Scheduling Checks (Polling `SELECT * WHERE updated_at > :last_poll`):**
  - **High I/O Overhead:** Forces recurring sequential or indexed scans across production tables, adding lock contention and cache churn on production buffer pools.
  - **Missed Intermediary Changes:** If a row undergoes multiple updates between polling intervals, intermediary states are lost.
  - **Inability to Capture Hard Deletes:** Polling queries cannot detect deleted rows unless the application maintains soft deletes (`is_deleted = TRUE`).
- **Log-Based CDC (WAL Parsing / Event Triggers):**
  - **Minimal Impact:** Log-based CDC asynchronously reads the database engine's native Write-Ahead Log (WAL) or captures changes during row modification.
  - **Complete Historical Fidelity:** Every individual mutation (`INSERT`, `UPDATE`, `DELETE`) is captured sequentially with exact transaction timestamps.
  - **Zero Polling Query Cost:** Avoids scanning production application tables, decoupling analytical extraction from transactional throughput.

---

### Question 2: How does your downstream replication engine handle network connection failures without losing event order or creating duplicate data writes?
1. **Deterministic Monotonic Sequence Ordering:** All events are captured with an auto-incrementing `BIGSERIAL event_id`. The consumer fetches pending changes ordered strictly by `ORDER BY event_id ASC`.
2. **Transaction Checkpointing:** The analytical table update and the audit ledger checkpoint (`UPDATE cdc_audit_ledger SET is_processed = TRUE`) execute inside the **same atomic database transaction**. If network fails mid-replication, the entire batch rolls back, leaving the checkpoint untouched.
3. **Idempotent Upserts:** Replay uses `ON CONFLICT (item_id) DO UPDATE ... WHERE analytical_inventory.replicated_version < EXCLUDED.replicated_version`. If a batch is re-delivered after an unexpected process crash, already applied rows are safely ignored.

---

### Question 3: What role does the transaction write-ahead log (WAL) fill in enabling real-time zero-impact CDC pipelines in production?
In enterprise production architectures (e.g., using Debezium or PostgreSQL Logical Decoding via `pgoutput`), CDC does not use application triggers. Instead:
- When PostgreSQL executes any transaction, it writes changes sequentially to the **Write-Ahead Log (WAL)** on disk before modifying table heap pages.
- CDC engines attach as a **logical replication slot**. PostgreSQL's background decoding process parses changes directly from the WAL stream.
- **Zero Query Overhead:** No extra SQL queries or trigger executions are added to the application's transaction path.
- **Zero Table Overhead:** No intermediary audit tables are written, minimizing table bloat and lock contention.

---

## 7. Supplementary Problem Implementation
**Requirement:** Implement a downstream deduplication logic check that handles out-of-order CDC updates by tracking database row version numbers.

**Implementation Details:**
- Implemented in `src/cdc_consumer.py`.
- Source table tracks monotonic `row_version` automatically incremented by `trg_bump_version`.
- When the consumer reads an event:
  ```python
  if row_version <= current_analytical_version:
      return False, "STALE_OR_DUPLICATE"
  ```
- Target updates enforce:
  ```sql
  WHERE analytical_inventory.replicated_version < EXCLUDED.replicated_version;
  ```
- Any re-transmitted or out-of-order event carrying an older version number is safely recorded as processed in the ledger without overwriting the newer state in the analytical target.
