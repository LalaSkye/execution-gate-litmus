def authority_gate(verdict):
    """Return True only if authority explicitly allows execution."""
    if verdict == "ALLOW":
        return True
    if verdict in ["DENY", None]:
        return False
