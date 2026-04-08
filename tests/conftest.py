"""Shared pytest fixtures for the Google TTS Studio test suite.

All factories and fixtures are defined here so individual test files can
import them without duplicating helper logic.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.domain.models import (
    AudioEncoding,
    HistoryEntry,
    InputMode,
    TTSRequest,
    TTSResult,
    TTSSettings,
)
from src.ports.tts_port import ITTSPort


# ── Voice data ────────────────────────────────────────────────────────────────

SAMPLE_VOICES = [
    {
        "name": "en-US-Neural2-C",
        "language_codes": ["en-US"],
        "ssml_gender": "FEMALE",
        "natural_sample_rate_hertz": 24000,
    },
    {
        "name": "en-US-Neural2-D",
        "language_codes": ["en-US"],
        "ssml_gender": "MALE",
        "natural_sample_rate_hertz": 24000,
    },
    {
        "name": "fr-FR-Neural2-A",
        "language_codes": ["fr-FR"],
        "ssml_gender": "FEMALE",
        "natural_sample_rate_hertz": 24000,
    },
    {
        "name": "de-DE-Neural2-B",
        "language_codes": ["de-DE"],
        "ssml_gender": "MALE",
        "natural_sample_rate_hertz": 24000,
    },
]


@pytest.fixture
def sample_voices() -> list[dict]:
    """Return a stable list of voice dicts for testing."""
    return list(SAMPLE_VOICES)


# ── TTSRequest factory ────────────────────────────────────────────────────────

def make_tts_request(
    text: str = "Hello world",
    encoding: str = "MP3",
    input_mode: InputMode = InputMode.TEXT,
    effects_profile_id: str | None = None,
    language_code: str = "en-US",
    voice_name: str = "en-US-Neural2-C",
    ssml_gender: str = "NEUTRAL",
    speaking_rate: float = 1.0,
    pitch: float = 0.0,
    volume_gain_db: float = 0.0,
    api_key: str = "fake-api-key",
) -> TTSRequest:
    """Factory for TTSRequest test instances."""
    settings = TTSSettings(
        language_code=language_code,
        voice_name=voice_name,
        ssml_gender=ssml_gender,
        audio_encoding=AudioEncoding.from_str(encoding),
        speaking_rate=speaking_rate,
        pitch=pitch,
        volume_gain_db=volume_gain_db,
        effects_profile_id=effects_profile_id,
        input_mode=input_mode,
    )
    return TTSRequest(text=text, settings=settings, api_key=api_key)


@pytest.fixture
def tts_request() -> TTSRequest:
    """Default TTSRequest fixture."""
    return make_tts_request()


# ── HistoryEntry factory ──────────────────────────────────────────────────────

def make_history_entry(
    title: str = "My Title",
    text: str = "Hello world",
    encoding: str = "MP3",
    settings: dict | None = None,
) -> dict:
    """Factory that creates a HistoryEntry and serialises it to dict,
    mirroring what the generate_speech use case produces."""
    import dataclasses
    entry = HistoryEntry(
        id=str(uuid.uuid4()),
        title=title,
        text_snippet=text[:80],
        full_text=text,
        timestamp=datetime.now(timezone.utc).isoformat(),
        encoding=encoding,
        settings=settings or {"language_code": "en-US"},
    )
    return dataclasses.asdict(entry)


@pytest.fixture
def history_entry() -> dict:
    """Default serialised HistoryEntry fixture."""
    return make_history_entry()


# ── Mock ITTSPort ─────────────────────────────────────────────────────────────

def make_mock_tts_adapter(
    audio_b64: str = "dGVzdGF1ZGlv",
    voices: list[dict] | None = None,
) -> MagicMock:
    """Return a MagicMock that implements ITTSPort for unit tests."""
    mock = MagicMock(spec=ITTSPort)
    mock.synthesize.return_value = TTSResult(
        audio_content_b64=audio_b64,
        encoding="MP3",
        character_count=11,
    )
    mock.list_voices.return_value = voices if voices is not None else list(SAMPLE_VOICES)
    return mock


@pytest.fixture
def mock_tts_adapter() -> MagicMock:
    """Default mock ITTSPort fixture."""
    return make_mock_tts_adapter()
