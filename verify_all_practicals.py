import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

PRACTICALS = [
    {"num": 6, "name": "Storage Lifecycle Management", "test_file": "Practical_6/tests/test_lifecycle.py"},
    {"num": 7, "name": "Change Data Capture (CDC)", "test_file": "Practical_7/tests/test_cdc.py"},
    {"num": 8, "name": "Query Processing and Optimization", "test_file": "Practical_8/tests/test_optimization.py"},
    {"num": 9, "name": "Data Modeling for Analytics", "test_file": "Practical_9/tests/test_data_modeling.py"},
    {"num": 10, "name": "Batch and Streaming Transformations", "test_file": "Practical_10/tests/test_transformations.py"},
    {"num": 11, "name": "Data Serving, Reverse ETL, and Security", "test_file": "Practical_11/tests/test_security_and_sync.py"}
]

def run_all_verifications():
    print("=" * 80)
    print("ITUC301: DATA ENGINEERING - COMPREHENSIVE LABORATORY VERIFICATION")
    print("Validating Practicals 6 through 11")
    print("=" * 80)

    pytest_exe = ROOT_DIR / "venv" / "Scripts" / "pytest.exe"
    if not pytest_exe.exists():
        pytest_exe = "pytest"
    else:
        pytest_exe = str(pytest_exe)

    results = []

    for p in PRACTICALS:
        print(f"\n[Practical {p['num']}: {p['name']}]")
        test_path = ROOT_DIR / p["test_file"]
        if not test_path.exists():
            print(f"  FAILED: Test file not found: {test_path}")
            results.append((p["num"], p["name"], "MISSING_TEST_FILE", 1))
            continue

        cmd = [pytest_exe, str(test_path), "-v", "--tb=short"]
        res = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
        
        if res.returncode == 0:
            print(f"  STATUS: PASSED (All tests succeeded)")
            results.append((p["num"], p["name"], "PASSED", 0))
        else:
            print(f"  STATUS: FAILED (Exit code {res.returncode})")
            print(res.stdout)
            print(res.stderr)
            results.append((p["num"], p["name"], "FAILED", res.returncode))

    print("\n" + "=" * 80)
    print("FINAL VERIFICATION SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Practical':<15} {'Title':<45} {'Test Status'}")
    print("-" * 80)
    all_passed = True
    for num, title, status, code in results:
        status_str = "[PASSED]" if status == "PASSED" else "[FAILED]"
        print(f"Practical {num:<5} {title:<45} {status_str}")
        if status != "PASSED":
            all_passed = False

    print("=" * 80)
    if all_passed:
        print("ALL REMAINING PRACTICALS (6-11) VERIFIED AND 100% OPERATIONAL.")
    else:
        print("SOME PRACTICALS FAILED VERIFICATION. REVIEW LOGS ABOVE.")
    print("=" * 80)

if __name__ == "__main__":
    run_all_verifications()
