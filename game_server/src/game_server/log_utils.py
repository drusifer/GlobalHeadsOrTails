def mask_key(key: str) -> str:
    """Show only first/last 4 chars of a secret key for safe logging."""
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"
