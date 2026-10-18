# Practical 6: Storage Lifecycle Management

## 1. Title and Objective
**Title:** Automated Storage Lifecycle Policy Matrix and Multi-Tier Archival System  
**Course Code:** ITUC301 – Data Engineering  
**Objective:** Formulate, implement, and validate an automated storage lifecycle policy matrix that classifies historical operational logs into three distinct access tiers—**Hot** (immediate access), **Warm** (infrequent access), and **Cold** (deep compressed archival)—based on retention targets, query frequency, and age constraints to optimize operational infrastructure costs while ensuring high data availability.

---

## 2. Tools and Technologies Used
- **MinIO Object Store / AWS S3 API:** Distributed object storage server with S3 API compatibility.
- **Python 3.x (`boto3`, `botocore`):** Automation scripts for policy evaluation, bucket operations, and checksum validation.
- **JSON Policy Schemas:** Declarative definitions of lifecycle transition matrix and retention rules.
- **Gzip Compression:** Stream-level compression for cold archival storage.
- **Docker Compose:** Containerized orchestration for local MinIO deployment.
- **Pytest:** Automated verification test suite.

---

## 3. Architecture and Tiering Workflow

```
+-----------------------------------------------------------------------------------+
|                           Operational System Logs                                 |
+-----------------------------------------------------------------------------------+
                                      |
                           [Policy Engine Evaluator]
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
  Age <= 30d OR                Age 31-90d AND                 Age > 90d OR
  Freq >= 5/wk                 Freq < 5/wk                    Inactive > 90d
         |                            |                            |
         v                            v                            v
   +-----------+               +-------------+              +-------------+
   |  HOT TIER |               |  WARM TIER  |              |  COLD TIER  |
   | logs-hot  |               |  logs-warm  |              |  logs-cold  |
   +-----------+               +-------------+              +-------------+
   (Uncompressed,              (Uncompressed,               (Gzip compressed,
    Low Latency,                Infrequent,                  Low Cost,
    $0.023/GB/mo)               $0.0125/GB/mo)               $0.004/GB/mo)
```

### Safety and Verification Rules:
1. **Verification Before Deletion:** Before deleting any source object from `logs-hot`, the engine computes the destination object MD5 and verifies byte lengths. If checksum or length diverges, the source object is preserved, and an alert is logged.
2. **Safe Idempotency:** Re-running the pipeline checks existing destination objects and does not corrupt or duplicate data.
3. **Structured Audit Trail:** Every evaluation, transition, verification, and demotion is logged with timestamps in `outputs/transition_audit.log`.

---

## 4. Directory Structure
```
Practical_6/
├── config/
│   └── lifecycle_policy.json        # Declarative JSON policy matrix
├── data/                            # Generated synthetic logs and manifests
├── outputs/                         # Classification reports, audit logs, and cost savings
├── src/
│   ├── access_log_analyzer.py       # Supplementary problem: >90d inactive demotion
│   ├── audit_logger.py              # Structured JSON audit logging
│   ├── cost_calculator.py           # Storage cost savings calculator
│   ├── data_generator.py            # Multi-quarter log and access manifest generator
│   ├── lifecycle_engine.py          # Policy matrix evaluation and transition logic
│   └── storage_client.py            # MinIO / S3 operations with MD5 verification
├── tests/
│   └── test_lifecycle.py            # Pytest test suite
├── docker-compose.yml               # Local MinIO service definition
├── .env.example                     # Environment configuration template
├── requirements.txt                 # Python dependencies
├── main.py                          # Pipeline entry point
└── README.md                        # Complete documentation
```

---

## 5. Prerequisites & Execution Instructions

### A. Environment Setup
```powershell
# From project root, activate virtual environment
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r Practical_6\requirements.txt
```

### B. MinIO Service Startup (Docker)
```powershell
cd Practical_6
docker compose up -d
```
MinIO will be accessible at:
- S3 API: `http://127.0.0.1:9000`
- Web Console: `http://127.0.0.1:9001` (Credentials: `minioadmin` / `minioadmin`)

### C. Run the Lifecycle Pipeline
```powershell
python main.py
```

### D. Run Automated Tests
```powershell
pytest tests/ -v
```

---

## 6. Answers to Key Evaluation Questions

### Question 1: Detail the hardware and software properties that differentiate high-throughput Hot tier storage pools from highly compressed Cold tier archiving solutions.
- **Hardware Profile:**
  - **Hot Tier:** Built upon high-IOPS NVMe SSDs or enterprise SAS arrays configured in RAID 10. Memory caching layers (RAM/Redis) are utilized for index caching, with multi-gigabit redundant network interfaces (25/100 GbE) to support low-latency parallel access.
  - **Cold Tier:** Built upon high-density, low-RPM mechanical hard drives (e.g., Shingled Magnetic Recording - SMR) or tape storage with higher latency tolerance, maximizing raw terabytes per dollar rather than random IOPS.
- **Software & Protocol Profile:**
  - **Hot Tier:** Maintains uncompressed or lightweight compressed data (e.g., Snappy/LZ4) to eliminate CPU decompression overhead. Metadata is heavily indexed in memory for sub-millisecond object lookup.
  - **Cold Tier:** Implements high-ratio block/file compression algorithms (e.g., Gzip-9, Zstandard, Bzip2) and erasure coding with high parity-to-data block efficiency. Object retrieval undergoes decompression workflows and may incur hydration/retrieval wait periods.

---

### Question 2: What are the typical operational and financial cost penalties incurred when an enterprise misclassifies historical active data into Cold states prematurely?
1. **Hydration & Retrieval Fees:** Cloud object stores (AWS S3 Glacier, Azure Archive, Google Coldline) charge significant data retrieval penalties per GB retrieved, along with expedited retrieval charges.
2. **Application Latency Penalties:** Applications requesting cold data face severe latency penalties (milliseconds to hours if archived on tape), resulting in API timeouts, stalled batch jobs, and disrupted customer dashboards.
3. **Early Deletion Penalties:** Most cold storage tiers impose minimum retention commitments (e.g., 90 or 180 days). If data is promoted back to Hot or deleted prematurely, the enterprise is billed for the remainder of the minimum commitment duration.
4. **Compute Overhead:** Recompressing and decompressing volatile data repeatedly consumes significant CPU cycles and compute instance bandwidth.

---

### Question 3: Explain how automated expiration policies safeguard database systems against structural performance degradation over long operational windows.
1. **B-Tree Index Bloat Reduction:** Continuous insertions into transactional tables cause B-tree indexes to fragment and expand. Pruning aged records maintains lean, balanced index pages that fit in RAM buffer pools.
2. **Table Scan and Vacuum Overhead Mitigation:** In MVCC engines like PostgreSQL, massive bloated tables increase sequential scan runtimes and impose intense autovacuum I/O workloads. Automated expiration purges dead tuples and caps table physical size.
3. **Query Optimization Predictability:** The query optimizer relies on statistics (histograms). Excessively skewed tables spanning several historical years with millions of stale rows degrade query selectivity estimates, leading to suboptimal hash joins and nested loops.
4. **Storage Predictability:** Eliminates unexpected storage exhaustion, ensuring high operational uptime.

---

## 7. Supplementary Problem Implementation
**Requirement:** Create an automation script that evaluates data access logs, flags data tables/objects that have not been read for more than 90 days, and automatically demotes their storage allocation tier via API calls.

**Implementation Details:**
- Implemented in `src/access_log_analyzer.py`.
- The analyzer scans `access_time_manifest.json` and evaluates `days_since_last_access`.
- Any object with `days_since_last_access > 90` is flagged for demotion, verified for integrity, and transferred into the compressed `logs-cold` bucket.
- Execution logs and demoted objects are exported to `outputs/access_analysis_report.json`.
