"""Authority gate — fail-closed by design.

Only exact string "ALLOW" permits execution.
Everything else — DENY, None, unknown, junk — returns False.
No implicit fall-through. No truthy/falsy ambiguity.
"""

def authority_gate(verdict):
    """Return True only if verdict is exactly 'ALLOW'. All else → False."""
    if verdict == "ALLOW":
        return True
    return False
