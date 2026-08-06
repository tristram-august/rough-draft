from __future__ import annotations


def anon_key_from_header(x_client_id: str | None) -> str | None:
    """Validate an X-Client-Id header into a usable anonymous voter/liker key."""
    if not x_client_id:
        return None
    x_client_id = x_client_id.strip()
    if len(x_client_id) < 8 or len(x_client_id) > 64:
        return None
    return x_client_id
