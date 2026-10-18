# Storage Lifecycle Management - Cost & Tiering Report

## 1. Executive Summary
- **Total Objects Managed:** 50
- **Total Volume:** 0.000293 GB (314812 bytes)
- **Baseline Cost (All Hot):** $0.000007 USD / month
- **Optimized Tiered Cost:** $0.000003 USD / month
- **Estimated Savings:** **$0.000004 USD / month (52.54%)**

## 2. Storage Tier Distribution
| Tier | Object Count | Storage (GB) | Applied Rate ($/GB/mo) | Monthly Cost ($) |
|------|-------------|--------------|------------------------|------------------|
| **HOT** | 20 | 0.000112 | $0.0230 | $0.000003 |
| **WARM** | 10 | 4.5e-05 | $0.0125 | $0.000001 |
| **COLD** | 20 | 1.2e-05 | $0.0040 | $0.000000 |

## 3. Inactive Data Demotion (>90 Days)
- **Objects Inactive > 90 Days:** 20
- **Policy Applied:** Automatically transitioned to deep compression `logs-cold` with gzip compression.
