"""
Small helper to run the same per-zone work across multiple zones
CONCURRENTLY instead of one-after-another. Our external API calls
(requests library) are blocking I/O, so Python threads genuinely
parallelize them (the GIL releases during network waits) -- this turns
"sum of every zone's wait time" into "roughly the slowest single zone's
wait time", which is the real fix for multi-zone endpoints (Enforcement,
Validation, city overview) being slow, rather than just tuning timeouts.
"""
from concurrent.futures import ThreadPoolExecutor


def run_parallel(items, fn, max_workers=10):
    """Run fn(item) for every item in items, concurrently, and return
    results in the SAME ORDER as items (not completion order) so callers
    can rely on positional correspondence."""
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        return list(pool.map(fn, items))