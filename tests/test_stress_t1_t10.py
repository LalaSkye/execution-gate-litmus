"""
MORPHEUS_STRESS_TEST_v1 — Execution Gate
ROUTE: TRINITY → MORPHEUS
MODE: NON_EXEC (TEST ONLY)
OBJECT: execution-gate-litmus + Trinity Stack v1

GOAL: Attempt to reach EXECUTION without a valid,
      authority-bound decision state.

PASS: Execution is impossible without authority_verdict == ALLOW
FAIL: Any path allows execution via interpretation,
      reconstruction, default allow, async delay,
      or identity ambiguity.
"""

import sys
import os
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sim"))

from gate import authority_gate
from action_simulator import execute_action

results = []

def record(test_id, name, passed, failure_mode="", reachability=""):
    status = "PASS" if passed else "FAIL"
    results.append({
        "id": test_id, "name": name, "status": status,
        "failure_mode": failure_mode, "reachability": reachability,
    })
    print(f"  [{status}] {test_id} — {name}")
    if not passed:
        print(f"         FAILURE_MODE: {failure_mode}")
        print(f"         REACHABILITY: {reachability}")


# ═══════════════════════════════════════════════════════════════
print("MORPHEUS_STRESS_TEST_v1")
print("=" * 60)


# ── T1: Missing Authority ─────────────────────────────────────
# INPUT: action with no authority_verdict
# EXPECT: HOLD (no execution)
gate_result = authority_gate(None)
action_result = execute_action(gate_result)
record("T1", "Missing Authority",
       passed=(gate_result == False and action_result == "BLOCKED"))


# ── T2: Delayed Authority (TOCTOU) ───────────────────────────
# INPUT: authority_verdict arrives AFTER execution trigger
# EXPECT: HOLD until resolved
# Test: gate is called with None first, then ALLOW arrives later.
#       The first gate call must block. Late arrival must not
#       retroactively validate the first call.

gate_before = authority_gate(None)
action_before = execute_action(gate_before)

# Now authority arrives — but the action already attempted
gate_after = authority_gate("ALLOW")
# The question: does the first action stay blocked?

record("T2", "Delayed Authority (TOCTOU)",
       passed=(action_before == "BLOCKED"),
       failure_mode="execution proceeded before authority arrived" if action_before != "BLOCKED" else "",
       reachability="async delay between trigger and verdict" if action_before != "BLOCKED" else "")


# ── T3: Identity Ambiguity ────────────────────────────────────
# INPUT: conflicting or unverifiable identity at gate
# EXPECT: HOLD
# Test: pass identity-like but non-ALLOW values

ambiguous_identities = [
    {"ALLOW": True},           # dict that contains ALLOW
    ["ALLOW"],                 # list that contains ALLOW
    type("Verdict", (), {"value": "ALLOW"})(),  # object with ALLOW attribute
    "ALLOW_FROM_UNVERIFIED",   # string containing ALLOW
]

t3_pass = True
t3_failure = ""
for i, identity in enumerate(ambiguous_identities):
    g = authority_gate(identity)
    a = execute_action(g)
    if a == "EXECUTED":
        t3_pass = False
        t3_failure = f"ambiguous identity variant {i} ({type(identity).__name__}) reached execution"
        break

record("T3", "Identity Ambiguity",
       passed=t3_pass,
       failure_mode=t3_failure,
       reachability="system accepted non-string identity as ALLOW" if not t3_pass else "")


# ── T4: Reconstruction Attack ─────────────────────────────────
# INPUT: logs + traces imply authority after execution
# EXPECT: DENY (post-hoc invalid)
# Test: execute with None, then try to "reconstruct" legitimacy
#       by calling gate with ALLOW after the fact.

gate_pre = authority_gate(None)
action_pre = execute_action(gate_pre)
# Post-hoc: "but look, authority existed!"
gate_posthoc = authority_gate("ALLOW")

# The original action must remain BLOCKED regardless
record("T4", "Reconstruction Attack",
       passed=(action_pre == "BLOCKED"),
       failure_mode="post-hoc authority retroactively validated execution" if action_pre != "BLOCKED" else "",
       reachability="reconstructed legitimacy from later verdict" if action_pre != "BLOCKED" else "")


# ── T5: Partial Evidence ──────────────────────────────────────
# INPUT: incomplete mandate / delegation chain
# EXPECT: HOLD
# Test: pass partial strings, substrings of ALLOW

partial_evidence = [
    "ALLO",       # truncated
    "LLOW",       # shifted
    "A",          # first char
    "AL",         # partial
    "ALLOW?",     # with qualifier
    "ALLOW*",     # with wildcard
    "ALLOW ",     # trailing space
]

t5_pass = True
t5_failure = ""
for p in partial_evidence:
    g = authority_gate(p)
    a = execute_action(g)
    if a == "EXECUTED":
        t5_pass = False
        t5_failure = f"partial evidence '{p}' reached execution"
        break

record("T5", "Partial Evidence",
       passed=t5_pass,
       failure_mode=t5_failure,
       reachability="system accepted incomplete mandate" if not t5_pass else "")


# ── T6: Override Injection ────────────────────────────────────
# INPUT: override flag without explicit authority binding
# EXPECT: DENY or HOLD
# Test: attempt to bypass gate with override-like values

overrides = [
    "OVERRIDE",
    "ADMIN_ALLOW",
    "SUDO",
    "FORCE",
    "BYPASS",
    "EMERGENCY_ALLOW",
    "__ALLOW__",
    "ALLOW\x00OVERRIDE",
]

t6_pass = True
t6_failure = ""
for o in overrides:
    g = authority_gate(o)
    a = execute_action(g)
    if a == "EXECUTED":
        t6_pass = False
        t6_failure = f"override '{o}' bypassed gate"
        break

record("T6", "Override Injection",
       passed=t6_pass,
       failure_mode=t6_failure,
       reachability="override flag accepted as authority" if not t6_pass else "")


# ── T7: Parallel Race ────────────────────────────────────────
# INPUT: two concurrent actions, one authorised, one not
# EXPECT: only authorised executes
# Test: simulate parallel execution with threading

race_results = {"authorised": None, "unauthorised": None}

def run_authorised():
    g = authority_gate("ALLOW")
    race_results["authorised"] = execute_action(g)

def run_unauthorised():
    g = authority_gate(None)
    race_results["unauthorised"] = execute_action(g)

t1_thread = threading.Thread(target=run_authorised)
t2_thread = threading.Thread(target=run_unauthorised)

# Run concurrently
t1_thread.start()
t2_thread.start()
t1_thread.join(timeout=5)
t2_thread.join(timeout=5)

t7_pass = (race_results["authorised"] == "EXECUTED" and
           race_results["unauthorised"] == "BLOCKED")

record("T7", "Parallel Race",
       passed=t7_pass,
       failure_mode=f"authorised={race_results['authorised']}, unauthorised={race_results['unauthorised']}" if not t7_pass else "",
       reachability="cross-authorisation leakage in concurrent execution" if not t7_pass else "")


# ── T8: Silent Default ────────────────────────────────────────
# INPUT: system timeout / no decision
# EXPECT: HOLD (no execution)
# Test: simulate timeout by passing various "empty" states

silent_defaults = [
    None,       # no decision
    "",         # empty string
    0,          # zero
    False,      # boolean false
    {},         # empty dict
    [],         # empty list
    b"",        # empty bytes
]

t8_pass = True
t8_failure = ""
for s in silent_defaults:
    g = authority_gate(s)
    a = execute_action(g)
    if a == "EXECUTED":
        t8_pass = False
        t8_failure = f"silent default {repr(s)} triggered execution"
        break

record("T8", "Silent Default",
       passed=t8_pass,
       failure_mode=t8_failure,
       reachability="default-allow on timeout/empty state" if not t8_pass else "")


# ── T9: Delegation Break ─────────────────────────────────────
# INPUT: authority exists but delegation chain broken
# EXPECT: HOLD
# Test: pass authority through intermediate that transforms it

class BrokenDelegation:
    """Simulates a broken delegation chain — authority exists
    somewhere in the chain but is not directly bound."""
    def __init__(self):
        self.original_verdict = "ALLOW"
        self.delegated = True
    def __str__(self):
        return "ALLOW"  # str() returns ALLOW but object is not "ALLOW"
    def __eq__(self, other):
        # Attempt to trick equality check
        if other == "ALLOW":
            return True
        return NotImplemented

broken = BrokenDelegation()
g = authority_gate(broken)
a = execute_action(g)

# The object's __eq__ returns True for == "ALLOW", so gate might be tricked
record("T9", "Delegation Break",
       passed=(a == "BLOCKED"),
       failure_mode="broken delegation chain tricked equality check" if a != "BLOCKED" else "",
       reachability="object.__eq__ spoofed ALLOW identity" if a != "BLOCKED" else "")


# ── T10: Replay Attack ────────────────────────────────────────
# INPUT: reuse of previous valid decision state
# EXPECT: DENY unless explicitly bound to new action
# Test: gate returns True for ALLOW — if that True is captured
#       and replayed, does a new action execute?

# First: legitimate action
legitimate_gate = authority_gate("ALLOW")
legitimate_action = execute_action(legitimate_gate)

# Now: replay the gate result (True) without new authority check
replayed_result = legitimate_gate  # captured from previous call
replayed_action = execute_action(replayed_result)

# This is the structural question: the gate itself is stateless,
# so replaying its output WILL execute. This is a design boundary.
# The gate does not track whether a verdict has been consumed.

if replayed_action == "EXECUTED":
    record("T10", "Replay Attack",
           passed=False,
           failure_mode="replayed gate result accepted — gate is stateless",
           reachability="captured True from prior authority_gate() call, "
                        "passed directly to execute_action() without new gate check")
else:
    record("T10", "Replay Attack", passed=True)


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

pass_count = sum(1 for r in results if r["status"] == "PASS")
fail_count = sum(1 for r in results if r["status"] == "FAIL")

for r in results:
    print(f"  {r['id']}: {r['status']}")

print(f"\nTOTAL: {pass_count} PASS, {fail_count} FAIL")

if fail_count == 0:
    print("VERDICT: execution is unreachable without authority under all tested conditions")
else:
    print(f"VERDICT: {fail_count} breach path(s) detected")
    print("\nBREACH PATHS:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  {r['id']} — {r['name']}")
            print(f"    FAILURE_MODE: {r['failure_mode']}")
            print(f"    REACHABILITY: {r['reachability']}")

sys.exit(0 if fail_count == 0 else 1)
