import json
import sys
from pathlib import Path

PRAC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRAC_DIR))

import pytest
from src.audit_logger import AuditLogger
from src.lifecycle_engine import LifecyclePolicyEngine
from src.access_log_analyzer import AccessLogAnalyzer
from src.cost_calculator import StorageCostCalculator

PRAC_DIR = Path(__file__).resolve().parent.parent

@pytest.fixture
def policy_engine(tmp_path):
    audit_log = tmp_path / "test_audit.log"
    logger = AuditLogger(audit_log)
    policy_path = PRAC_DIR / "config" / "lifecycle_policy.json"
    return LifecyclePolicyEngine(policy_path, logger, storage_client=None)

def test_hot_tier_classification(policy_engine):
    meta_recent = {"object_key": "rec.log", "age_days": 10, "access_count_last_7_days": 12, "days_since_last_access": 1}
    assert policy_engine.evaluate_object(meta_recent) == "HOT"

    meta_frequent = {"object_key": "freq.log", "age_days": 25, "access_count_last_7_days": 6, "days_since_last_access": 2}
    assert policy_engine.evaluate_object(meta_frequent) == "HOT"

def test_warm_tier_classification(policy_engine):
    meta_warm = {"object_key": "warm.log", "age_days": 45, "access_count_last_7_days": 2, "days_since_last_access": 15}
    assert policy_engine.evaluate_object(meta_warm) == "WARM"

def test_cold_tier_classification(policy_engine):
    # Old object
    meta_old = {"object_key": "old.log", "age_days": 120, "access_count_last_7_days": 0, "days_since_last_access": 100}
    assert policy_engine.evaluate_object(meta_old) == "COLD"

    # Inactive > 90 days despite age
    meta_inactive = {"object_key": "inact.log", "age_days": 92, "access_count_last_7_days": 0, "days_since_last_access": 95}
    assert policy_engine.evaluate_object(meta_inactive) == "COLD"

def test_expired_tier_classification(policy_engine):
    meta_expired = {"object_key": "exp.log", "age_days": 400, "access_count_last_7_days": 0, "days_since_last_access": 390}
    assert policy_engine.evaluate_object(meta_expired) == "EXPIRED"

def test_access_log_analyzer_flags_90_days(tmp_path):
    audit_log = tmp_path / "analyzer_audit.log"
    logger = AuditLogger(audit_log)
    analyzer = AccessLogAnalyzer(logger, storage_client=None)

    metadata = [
        {"object_key": "active.log", "days_since_last_access": 10, "age_days": 20, "size_bytes": 1000},
        {"object_key": "dormant.log", "days_since_last_access": 95, "age_days": 110, "size_bytes": 2000},
        {"object_key": "ancient.log", "days_since_last_access": 150, "age_days": 200, "size_bytes": 3000}
    ]

    flagged, count = analyzer.analyze_and_demote_inactive(metadata, inactivity_threshold_days=90)
    assert len(flagged) == 2
    assert flagged[0]["object_key"] == "dormant.log"
    assert flagged[1]["object_key"] == "ancient.log"

def test_storage_cost_calculator():
    calculator = StorageCostCalculator(hot_rate=0.023, warm_rate=0.0125, cold_rate=0.004)
    # 1 GB = 1073741824 bytes
    gb_bytes = 1073741824
    test_objects = [
        {"object_key": "h.log", "size_bytes": gb_bytes, "target_tier": "HOT"},
        {"object_key": "w.log", "size_bytes": gb_bytes, "target_tier": "WARM"},
        {"object_key": "c.log", "size_bytes": gb_bytes, "target_tier": "COLD", "transition_details": {"dest_size": int(gb_bytes * 0.4)}}
    ]
    report = calculator.calculate_savings(test_objects)
    assert report["total_objects"] == 3
    assert report["baseline_all_hot_cost_usd"] > report["optimized_tiered_cost_usd"]
    assert report["savings_percentage"] > 40.0
