"""Tiny in-memory TTL cache so a live demo doesn't hammer free public APIs
(Overpass in particular rate-limits aggressively) on every UI click."""
import time
from config import CACHE_TTL_SECONDS

_store = {}


def cache_get(key):
    entry = _store.get(key)
    if not entry:
        return None
    value, expires_at = entry
    if time.time() > expires_at:
        _store.pop(key, None)
        return None
    return value


def cache_set(key, value, ttl=CACHE_TTL_SECONDS):
    _store[key] = (value, time.time() + ttl)
    return value