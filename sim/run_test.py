"""Execution Gate Litmus — v1 test runner."""

from gate import authority_gate
from action_simulator import execute_action

tests = [
    {"name": "NO_AUTHORITY", "verdict": None,    "expected": "BLOCKED"},
    {"name": "DENY",         "verdict": "DENY",  "expected": "BLOCKED"},
    {"name": "ALLOW",        "verdict": "ALLOW", "expected": "EXECUTED"},
]

passed = 0
failed = 0

for t in tests:
    allowed = authority_gate(t["verdict"])
    result = execute_action(allowed)
    status = "PASS" if result == t["expected"] else "FAIL"

    if status == "PASS":
        passed += 1
    else:
        failed += 1

    print(f"{t['name']}: {result} → {status}")

print(f"\n{'='*40}")
print(f"TOTAL: {passed} passed, {failed} failed")

if failed == 0:
    print("VERDICT: governance is load-bearing")
else:
    print("VERDICT: execution is reachable without authority")
