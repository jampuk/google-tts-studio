"""Tests for CachingTTSAdapter."""
import time
import pytest
from unittest.mock import MagicMock

from src.adapters.caching_tts_adapter import CachingTTSAdapter
from src.domain.models import TTSRequest, TTSSettings, TTSResult, AudioEncoding
from src.ports.tts_port import ITTSPort
from tests.conftest import make_mock_tts_adapter, make_tts_request, SAMPLE_VOICES


# ══════════════════════════════════════════════
# list_voices — cache behaviour
# ══════════════════════════════════════════════

class TestListVoicesCache:
    def test_first_call_delegates_to_adapter(self):
        delegate = make_mock_tts_adapter(voices=SAMPLE_VOICES)
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        result = adapter.list_voices(api_key="key")
        delegate.list_voices.assert_called_once_with(api_key="key", language_code=None)
        assert result == SAMPLE_VOICES

    def test_second_call_returns_cached_result(self):
        delegate = make_mock_tts_adapter(voices=SAMPLE_VOICES)
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        first = adapter.list_voices(api_key="key")
        second = adapter.list_voices(api_key="key")
        # Delegate called only once — second result from cache
        delegate.list_voices.assert_called_once()
        assert first == second

    def test_expired_cache_entry_re_fetches(self):
        delegate = make_mock_tts_adapter(voices=SAMPLE_VOICES)
        adapter = CachingTTSAdapter(delegate, ttl_seconds=0)  # expires immediately
        adapter.list_voices(api_key="key")
        # Force TTL expiry by sleeping past 0-second TTL
        time.sleep(0.01)
        adapter.list_voices(api_key="key")
        assert delegate.list_voices.call_count == 2

    def test_different_api_keys_get_separate_cache_entries(self):
        delegate = make_mock_tts_adapter(voices=SAMPLE_VOICES)
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        adapter.list_voices(api_key="key-A")
        adapter.list_voices(api_key="key-B")
        assert delegate.list_voices.call_count == 2

    def test_different_language_codes_get_separate_cache_entries(self):
        delegate = make_mock_tts_adapter(voices=SAMPLE_VOICES)
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        adapter.list_voices(api_key="key", language_code="en-US")
        adapter.list_voices(api_key="key", language_code="fr-FR")
        assert delegate.list_voices.call_count == 2

    def test_same_language_code_second_call_is_cached(self):
        delegate = make_mock_tts_adapter(voices=SAMPLE_VOICES)
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        adapter.list_voices(api_key="key", language_code="en-US")
        adapter.list_voices(api_key="key", language_code="en-US")
        delegate.list_voices.assert_called_once()

    def test_none_and_missing_language_code_share_cache_entry(self):
        """Both None and omitting language_code should hit the same cache slot."""
        delegate = make_mock_tts_adapter(voices=SAMPLE_VOICES)
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        adapter.list_voices(api_key="key", language_code=None)
        adapter.list_voices(api_key="key")  # language_code defaults to None
        delegate.list_voices.assert_called_once()

    def test_invalidate_clears_all_entries(self):
        delegate = make_mock_tts_adapter(voices=SAMPLE_VOICES)
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        adapter.list_voices(api_key="key-A")
        adapter.list_voices(api_key="key-B")
        adapter.invalidate()
        # Both entries cleared — next calls re-fetch
        adapter.list_voices(api_key="key-A")
        adapter.list_voices(api_key="key-B")
        assert delegate.list_voices.call_count == 4

    def test_returns_list_from_cache_unchanged(self):
        voices = [{"name": "en-US-Neural2-C"}]
        delegate = make_mock_tts_adapter(voices=voices)
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        adapter.list_voices(api_key="key")
        result = adapter.list_voices(api_key="key")  # from cache
        assert result == voices

    def test_adapter_implements_port_interface(self):
        delegate = make_mock_tts_adapter()
        adapter = CachingTTSAdapter(delegate)
        assert isinstance(adapter, ITTSPort)


# ══════════════════════════════════════════════
# synthesize — always delegates, never caches
# ══════════════════════════════════════════════

class TestSynthesizePassthrough:
    def test_synthesize_delegates_to_underlying_adapter(self):
        delegate = make_mock_tts_adapter(audio_b64="dGVzdA==")
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        request = make_tts_request()
        result = adapter.synthesize(request)
        delegate.synthesize.assert_called_once_with(request)
        assert result.audio_content_b64 == "dGVzdA=="

    def test_synthesize_is_never_cached(self):
        """Two identical synthesize calls must both hit the delegate."""
        delegate = make_mock_tts_adapter()
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        request = make_tts_request()
        adapter.synthesize(request)
        adapter.synthesize(request)
        assert delegate.synthesize.call_count == 2

    def test_synthesize_propagates_value_error(self):
        delegate = make_mock_tts_adapter()
        delegate.synthesize.side_effect = ValueError("API error (HTTP 403)")
        adapter = CachingTTSAdapter(delegate, ttl_seconds=60)
        with pytest.raises(ValueError, match="403"):
            adapter.synthesize(make_tts_request())


# ══════════════════════════════════════════════
# Default TTL
# ══════════════════════════════════════════════

class TestDefaultTTL:
    def test_default_ttl_is_3600_seconds(self):
        delegate = make_mock_tts_adapter()
        adapter = CachingTTSAdapter(delegate)
        assert adapter._ttl == 3600
