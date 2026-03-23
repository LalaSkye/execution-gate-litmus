def execute_action(allowed):
    """Execute only if the gate returned True."""
    if allowed:
        return "EXECUTED"
    return "BLOCKED"
