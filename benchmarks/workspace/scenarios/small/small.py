"""A consumer of one small dependency without transitive Python packages."""

from cachetools import LRUCache

cache = LRUCache(maxsize=64)
cache["ready"] = 1


def cached_count(key: str) -> int:
    """Read a cached integer without accessing external services."""
    return cache[key]
