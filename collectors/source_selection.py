"""Environment-driven source selection for domestic/overseas collector nodes."""

import os


def selected_sources(env_name: str, available) -> set[str]:
    """Return enabled source names, defaulting to every available source."""
    available_set = set(available)
    raw = os.getenv(env_name)
    if raw is None or not raw.strip():
        return available_set
    requested = {item.strip().lower() for item in raw.split(',') if item.strip()}
    return requested & available_set


def optional_proxy(env_name: str, default: str = '') -> str:
    """Resolve a proxy URL; direct/none/off explicitly disable proxying."""
    value = os.getenv(env_name)
    if value is None:
        value = default
    value = value.strip()
    if value.lower() in {'direct', 'none', 'off', 'disabled'}:
        return ''
    return value
