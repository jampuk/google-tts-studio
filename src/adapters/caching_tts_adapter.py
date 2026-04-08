"""Caching decorator adapter for ITTSPort.

Wraps any ITTSPort implementation and caches list_voices() results in-process
with a configurable TTL.  synthesize() is always delegated directly — audio
results are unique per request and must never be cached.

Cache key design:
  SHA-256(api_key + "|" + (language_code or ""))

This ensures:
  - Different API keys get isolated cache entries.
  - Per-language queries are cached separately from all-language queries.

Thread safety:
  A threading.Lock protects all dict operations so the adapter is safe to use
  across Gunicorn threads (--threads N) without race conditions.
"""
import hashlib
import logging
import threading
import time
from typing import Optional

from src.domain.models import TTSRequest, TTSResult
from src.ports.tts_port import ITTSPort

logger = logging.getLogger(__name__)


class CachingTTSAdapter(ITTSPort):
    """ITTSPort decorator that caches list_voices() results with a TTL.

    Usage:
        adapter = CachingTTSAdapter(GoogleTTSAdapter(), ttl_seconds=3600)

    The cache is stored in process memory.  In a multi-worker Gunicorn
    deployment each worker maintains its own independent cache — this still
    reduces API calls per worker and avoids re-fetching on every callback
    within a worker's lifetime.

    synthesize() is always passed through to the delegate without caching
    because audio results depend on the full request payload and must not
    be reused across different text/settings combinations.
    """

    def __init__(self, delegate: ITTSPort, ttl_seconds: int = 3600) -> None:
        """
        Args:
            delegate: The underlying ITTSPort implementation to delegate to.
            ttl_seconds: How long (in seconds) a cached voice list is considered
                fresh.  After expiry the next call fetches from the API again.
                Default: 3600 (1 hour).
        """
        self._delegate = delegate
        self._ttl = ttl_seconds
        # _cache maps cache_key → (voices_list, expires_at_monotonic)
        self._cache: dict[str, tuple[list, float]] = {}
        self._lock = threading.Lock()

    # ── Cache helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _make_key(api_key: str, language_code: Optional[str]) -> str:
        """Return a stable, non-reversible cache key for the given parameters."""
        raw = f"{api_key}|{language_code or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get(self, key: str) -> Optional[list]:
        """Return cached voices if the entry exists and has not expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            voices, expires_at = entry
            if time.monotonic() > expires_at:
                del self._cache[key]
                return None
            return voices

    def _set(self, key: str, voices: list) -> None:
        """Store voices in the cache with a TTL-based expiry."""
        with self._lock:
            self._cache[key] = (voices, time.monotonic() + self._ttl)

    def invalidate(self) -> None:
        """Clear the entire voice cache.

        Useful when the user manually refreshes voices or saves a new API key.
        """
        with self._lock:
            self._cache.clear()
        logger.info("CachingTTSAdapter: voice cache invalidated")

    # ── ITTSPort implementation ────────────────────────────────────────────────

    def list_voices(self, api_key: str, language_code: Optional[str] = None) -> list:
        """Return voice list, served from cache when available.

        Cache miss → delegates to the underlying adapter and stores the result.
        Cache hit  → returns stored list immediately without an API call.
        """
        key = self._make_key(api_key, language_code)
        cached = self._get(key)

        if cached is not None:
            logger.debug(
                "CachingTTSAdapter: cache hit (language_code=%s, %d voices)",
                language_code or "all",
                len(cached),
            )
            return cached

        logger.info(
            "CachingTTSAdapter: cache miss — fetching from API (language_code=%s)",
            language_code or "all",
        )
        voices = self._delegate.list_voices(api_key=api_key, language_code=language_code)
        self._set(key, voices)
        logger.info(
            "CachingTTSAdapter: cached %d voices (TTL=%ds)",
            len(voices),
            self._ttl,
        )
        return voices

    def synthesize(self, request: TTSRequest) -> TTSResult:
        """Delegate synthesis directly — audio results are never cached."""
        return self._delegate.synthesize(request)
