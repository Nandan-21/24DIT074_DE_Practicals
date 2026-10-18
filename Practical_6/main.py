import json
import os
import sys
from pathlib import Path

# Add current practical root to sys.path
PRAC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PRAC_DIR))

from src.audit_logger import AuditLogger
from src.data_generator import generate_synthetic_operational_logs
from src.storage_client import StorageClient
from src.lifecycle_engine import LifecyclePolicyEngine
from src.access_log_analyzer import AccessLogAnalyzer
from src.cost_calculator import StorageCostCalculator

def run_pipeline():
    print("=" * 70)
    print("PRACTICAL 6: STORAGE LIFECYCLE MANAGEMENT")
    print("Automated Multi-Tier (Hot / Warm / Cold) Policy Engine & Analysis")
    print("=" * 70)

    outputs_dir = PRAC_DIR / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    audit_file = outputs_dir / "transition_audit.log"
    # Reset log for fresh idempotent run
    if audit_file.exists():
        audit_file.unlink()

    audit_logger = AuditLogger(audit_file)
    policy_path = PRAC_DIR / "config" / "lifecycle_policy.json"

    # Step 1: Generate synthetic operational logs spanning multiple quarters
    print("\n[Step 1] Generating synthetic operational logs spanning multiple quarters...")
    manifest, access_logs = generate_synthetic_operational_logs(PRAC_DIR, num_objects=50, seed=42)
    print(f"Generated {len(manifest)} operational log objects and {len(access_logs)} access events.")

    # Step 2: Storage client initialization
    print("\n[Step 2] Initializing MinIO Storage Client...")
    storage = StorageClient()
    minio_active = False
    try:
        storage.ensure_bucket("logs-hot")
        storage.ensure_bucket("logs-warm")
        storage.ensure_bucket("logs-cold")
        minio_active = True
        print("Connected to MinIO server successfully. Buckets initialized: logs-hot, logs-warm, logs-cold.")
        
        # Upload initial objects into HOT bucket
        print("Seeding initial dataset into 'logs-hot' bucket...")
        for item in manifest:
            storage.upload_file(
                bucket_name="logs-hot",
                object_key=item["object_key"],
                file_path=item["local_path"],
                metadata={"quarter": item["quarter"], "log_type": item["log_type"]}
            )
        print(f"Successfully uploaded {len(manifest)} objects to logs-hot.")
    except Exception as e:
        print(f"[NOTE] MinIO daemon connection not active on http://127.0.0.1:9000 ({e}).")
        print("MinIO can be started with 'docker compose up -d'. Running policy evaluation and verification in local mode.")

    # Step 3: Run Policy Evaluation & Tier Transitions
    print("\n[Step 3] Running Lifecycle Policy Engine...")
    engine = LifecyclePolicyEngine(policy_path, audit_logger, storage if minio_active else None)
    classified_objects, tier_counts = engine.process_all_objects(manifest, current_tier="HOT")

    print("\nClassification Summary:")
    for tier, count in tier_counts.items():
        print(f"  - {tier:10s}: {count} objects")

    # Step 4: Run Access Log Analyzer (Supplementary Problem: >90 days inactive demotion)
    print("\n[Step 4] Running Access-Log Analyzer (Supplementary Problem)...")
    analyzer = AccessLogAnalyzer(audit_logger, storage if minio_active else None)
    flagged, demoted_count = analyzer.analyze_and_demote_inactive(manifest, inactivity_threshold_days=90)
    print(f"Flagged {len(flagged)} objects inactive for > 90 days. Auto-demotions initiated: {demoted_count}.")

    # Step 5: Cost Savings Calculation
    print("\n[Step 5] Calculating Storage Cost Reductions...")
    calculator = StorageCostCalculator(hot_rate=0.023, warm_rate=0.0125, cold_rate=0.004)
    cost_report = calculator.calculate_savings(classified_objects)

    print(f"  Total Data Analyzed: {cost_report['total_size_bytes']} bytes ({cost_report['total_size_gb']} GB)")
    print(f"  Baseline All-Hot Cost:   ${cost_report['baseline_all_hot_cost_usd']:.6f} / month")
    print(f"  Optimized Tiered Cost:   ${cost_report['optimized_tiered_cost_usd']:.6f} / month")
    print(f"  Monthly Savings:         ${cost_report['monthly_savings_usd']:.6f} ({cost_report['savings_percentage']}%)")

    # Save output artifacts
    print("\n[Step 6] Persisting Reports & Audit Manifests...")
    with open(outputs_dir / "classification_report.json", "w", encoding="utf-8") as f:
        json.dump({"summary": tier_counts, "cost_analysis": cost_report, "objects": classified_objects}, f, indent=2)

    with open(outputs_dir / "access_analysis_report.json", "w", encoding="utf-8") as f:
        json.dump({"threshold_days": 90, "flagged_count": len(flagged), "flagged_objects": flagged}, f, indent=2)

    # Markdown cost breakdown
    md_report = f"""# Storage Lifecycle Management - Cost & Tiering Report

## 1. Executive Summary
- **Total Objects Managed:** {cost_report['total_objects']}
- **Total Volume:** {cost_report['total_size_gb']} GB ({cost_report['total_size_bytes']} bytes)
- **Baseline Cost (All Hot):** ${cost_report['baseline_all_hot_cost_usd']:.6f} USD / month
- **Optimized Tiered Cost:** ${cost_report['optimized_tiered_cost_usd']:.6f} USD / month
- **Estimated Savings:** **${cost_report['monthly_savings_usd']:.6f} USD / month ({cost_report['savings_percentage']}%)**

## 2. Storage Tier Distribution
| Tier | Object Count | Storage (GB) | Applied Rate ($/GB/mo) | Monthly Cost ($) |
|------|-------------|--------------|------------------------|------------------|
| **HOT** | {tier_counts.get('HOT', 0)} | {cost_report['tier_breakdown']['HOT']['gb']} | $0.0230 | ${cost_report['tier_breakdown']['HOT']['monthly_cost_usd']:.6f} |
| **WARM** | {tier_counts.get('WARM', 0)} | {cost_report['tier_breakdown']['WARM']['gb']} | $0.0125 | ${cost_report['tier_breakdown']['WARM']['monthly_cost_usd']:.6f} |
| **COLD** | {tier_counts.get('COLD', 0)} | {cost_report['tier_breakdown']['COLD']['gb']} | $0.0040 | ${cost_report['tier_breakdown']['COLD']['monthly_cost_usd']:.6f} |

## 3. Inactive Data Demotion (>90 Days)
- **Objects Inactive > 90 Days:** {len(flagged)}
- **Policy Applied:** Automatically transitioned to deep compression `logs-cold` with gzip compression.
"""
    with open(outputs_dir / "cost_savings_report.md", "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"Artifacts successfully written to {outputs_dir}")
    print("=" * 70)
    print("PRACTICAL 6 EXECUTION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_pipeline()
