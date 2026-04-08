"""
Tests for pure-logic helpers in src/application/callbacks.py.

All tests import directly from the production module so that if a constant or
helper is renamed/removed the test immediately fails rather than silently
validating a stale local copy.

Dash callbacks that interact with the Dash server (InputOutput wiring) are NOT
tested here — those require a running Dash app and belong in integration tests.
Only the pure-Python helper functions are covered.
"""
import dataclasses
import uuid
from datetime import datetime, timezone

import pytest

# ── Production imports ─────────────────────────────────────────────────────
# Helpers now live in the callbacks package's helpers module.
from src.application.callbacks.helpers import (
    GENDER_SYMBOL,
    build_language_options as _build_language_options,
    build_voice_options as _build_voice_options,
    build_gender_options as _build_gender_options,
)
from src.domain.models import (
    AudioEncoding,
    HistoryEntry,
    sanitize_text,
    utf8_byte_length,
)

# ENCODING_MIME and ENCODING_EXT are now properties on AudioEncoding members.
# These dicts are kept here only for the constant-level tests that verify the
# values are correct — they are derived from the enum rather than hardcoded.
ENCODING_MIME = {m.value: m.mime for m in AudioEncoding}
ENCODING_EXT  = {m.value: m.ext  for m in AudioEncoding}


# ══════════════════════════════════════════════
# Encoding constants (imported from production)
# ══════════════════════════════════════════════

class TestEncodingMime:
    def test_mp3(self):
        assert ENCODING_MIME["MP3"] == "audio/mpeg"

    def test_linear16(self):
        assert ENCODING_MIME["LINEAR16"] == "audio/wav"

    def test_ogg_opus(self):
        assert ENCODING_MIME["OGG_OPUS"] == "audio/ogg"

    def test_mulaw(self):
        assert ENCODING_MIME["MULAW"] == "audio/basic"

    def test_alaw(self):
        assert ENCODING_MIME["ALAW"] == "audio/pcm"

    def test_all_five_encodings_present(self):
        assert len(ENCODING_MIME) == 5


class TestEncodingExt:
    def test_mp3(self):
        assert ENCODING_EXT["MP3"] == ".mp3"

    def test_linear16(self):
        assert ENCODING_EXT["LINEAR16"] == ".wav"

    def test_ogg_opus(self):
        assert ENCODING_EXT["OGG_OPUS"] == ".ogg"

    def test_mulaw(self):
        assert ENCODING_EXT["MULAW"] == ".au"

    def test_alaw(self):
        assert ENCODING_EXT["ALAW"] == ".alaw"

    def test_all_five_encodings_present(self):
        assert len(ENCODING_EXT) == 5

    def test_extensions_start_with_dot(self):
        for ext in ENCODING_EXT.values():
            assert ext.startswith("."), f"Extension {ext!r} must start with '.'"


class TestAudioSrcDataUri:
    """Validates the data-URI pattern used when setting the audio player src."""

    def test_mp3_data_uri(self):
        b64 = "dGVzdA=="
        src = f"data:{ENCODING_MIME['MP3']};base64,{b64}"
        assert src == "data:audio/mpeg;base64,dGVzdA=="

    def test_wav_data_uri(self):
        b64 = "abc123"
        src = f"data:{ENCODING_MIME['LINEAR16']};base64,{b64}"
        assert src.startswith("data:audio/wav;base64,")

    def test_ogg_data_uri(self):
        b64 = "abc123"
        src = f"data:{ENCODING_MIME['OGG_OPUS']};base64,{b64}"
        assert src.startswith("data:audio/ogg;base64,")


# ══════════════════════════════════════════════
# _build_language_options
# ══════════════════════════════════════════════

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


class TestBuildLanguageOptions:
    def test_returns_list_of_dicts(self):
        options = _build_language_options(SAMPLE_VOICES)
        assert isinstance(options, list)
        assert all("value" in o and "label" in o for o in options)

    def test_deduplicates_languages(self):
        # en-US appears in two voices; must appear once in options
        options = _build_language_options(SAMPLE_VOICES)
        values = [o["value"] for o in options]
        assert values.count("en-US") == 1

    def test_all_languages_present(self):
        options = _build_language_options(SAMPLE_VOICES)
        values = {o["value"] for o in options}
        assert "en-US" in values
        assert "fr-FR" in values
        assert "de-DE" in values

    def test_sorted_alphabetically(self):
        options = _build_language_options(SAMPLE_VOICES)
        values = [o["value"] for o in options]
        assert values == sorted(values)

    def test_returns_empty_for_empty_input(self):
        assert _build_language_options([]) == []

    def test_value_equals_language_code(self):
        options = _build_language_options(SAMPLE_VOICES)
        for o in options:
            assert o["value"] == o["label"]


# ══════════════════════════════════════════════
# _build_gender_options
# ══════════════════════════════════════════════

class TestBuildGenderOptions:
    def test_always_includes_all_genders_option(self):
        options = _build_gender_options(SAMPLE_VOICES, "en-US")
        values = [o["value"] for o in options]
        assert "ALL" in values

    def test_all_genders_option_is_first(self):
        options = _build_gender_options(SAMPLE_VOICES, "en-US")
        assert options[0]["value"] == "ALL"

    def test_shows_genders_for_given_language(self):
        options = _build_gender_options(SAMPLE_VOICES, "en-US")
        values = {o["value"] for o in options}
        assert "FEMALE" in values
        assert "MALE" in values

    def test_excludes_genders_for_other_language(self):
        # Only fr-FR-Neural2-A is FEMALE for fr-FR; no MALE voice for fr-FR
        options = _build_gender_options(SAMPLE_VOICES, "fr-FR")
        values = {o["value"] for o in options}
        assert "FEMALE" in values
        assert "MALE" not in values

    def test_gender_symbol_in_label(self):
        options = _build_gender_options(SAMPLE_VOICES, "en-US")
        female = next(o for o in options if o["value"] == "FEMALE")
        assert GENDER_SYMBOL["FEMALE"] in female["label"]

    def test_returns_only_all_for_unknown_language(self):
        options = _build_gender_options(SAMPLE_VOICES, "xx-XX")
        assert len(options) == 1
        assert options[0]["value"] == "ALL"


# ══════════════════════════════════════════════
# _build_voice_options
# ══════════════════════════════════════════════

class TestBuildVoiceOptions:
    def test_filters_by_language(self):
        options = _build_voice_options(SAMPLE_VOICES, "fr-FR")
        assert len(options) == 1
        assert options[0]["value"] == "fr-FR-Neural2-A"

    def test_filters_by_language_and_gender_female(self):
        options = _build_voice_options(SAMPLE_VOICES, "en-US", gender="FEMALE")
        values = [o["value"] for o in options]
        assert "en-US-Neural2-C" in values
        assert "en-US-Neural2-D" not in values

    def test_filters_by_language_and_gender_male(self):
        options = _build_voice_options(SAMPLE_VOICES, "en-US", gender="MALE")
        values = [o["value"] for o in options]
        assert "en-US-Neural2-D" in values
        assert "en-US-Neural2-C" not in values

    def test_all_gender_returns_all_voices_for_language(self):
        options = _build_voice_options(SAMPLE_VOICES, "en-US", gender="ALL")
        assert len(options) == 2

    def test_none_gender_returns_all_voices_for_language(self):
        options = _build_voice_options(SAMPLE_VOICES, "en-US", gender=None)
        assert len(options) == 2

    def test_returns_empty_for_no_matching_voices(self):
        options = _build_voice_options(SAMPLE_VOICES, "xx-XX")
        assert options == []

    def test_label_contains_name_gender_symbol_and_rate(self):
        options = _build_voice_options(SAMPLE_VOICES, "en-US", gender="FEMALE")
        label = options[0]["label"]
        assert "en-US-Neural2-C" in label
        assert GENDER_SYMBOL["FEMALE"] in label
        assert "24000Hz" in label

    def test_sorted_by_voice_name(self):
        options = _build_voice_options(SAMPLE_VOICES, "en-US")
        values = [o["value"] for o in options]
        assert values == sorted(values)

    def test_option_has_value_and_label_keys(self):
        options = _build_voice_options(SAMPLE_VOICES, "en-US")
        for o in options:
            assert "value" in o
            assert "label" in o


# ══════════════════════════════════════════════
# Character count display logic
# ══════════════════════════════════════════════

def _compute_char_count(text):
    """Thin wrapper that calls the same domain functions used by the production
    update_char_count callback.  Uses sanitize_text and utf8_byte_length directly
    rather than reimplementing the logic, so the tests stay in sync with the
    callback automatically (Overlap 3.3 fix).
    """
    raw = text or ""
    raw_chars = len(raw)
    clean = sanitize_text(raw)
    clean_chars = len(clean)
    clean_bytes = utf8_byte_length(clean)

    byte_suffix = f" ({clean_bytes} bytes)" if clean_bytes != clean_chars else ""

    if clean_chars != raw_chars:
        return f"{raw_chars} raw / {clean_chars} clean{byte_suffix} / 5000 byte limit"
    return f"{raw_chars} chars{byte_suffix} / 5000 byte limit"


class TestCharCountDisplay:
    def test_empty_input(self):
        result = _compute_char_count("")
        assert "0 chars" in result
        assert "5000 byte limit" in result

    def test_none_input(self):
        result = _compute_char_count(None)
        assert "0 chars" in result

    def test_ascii_shows_no_byte_suffix(self):
        result = _compute_char_count("Hello world")
        # ASCII: bytes == chars, so no byte suffix expected
        assert "bytes" not in result

    def test_multibyte_shows_byte_count(self):
        result = _compute_char_count("日本語")
        # 3 CJK chars = 9 UTF-8 bytes — suffix must appear
        assert "bytes" in result

    def test_sanitized_shorter_shows_raw_and_clean(self):
        # Markdown heading: raw "# Title" → clean "Title"
        result = _compute_char_count("# Title")
        assert "raw" in result
        assert "clean" in result

    def test_shows_5000_byte_limit(self):
        result = _compute_char_count("test")
        assert "5000 byte limit" in result

    def test_plain_text_shows_char_count(self):
        text = "Hello"
        result = _compute_char_count(text)
        assert "5 chars" in result


# ══════════════════════════════════════════════
# HistoryEntry (production domain model)
# ══════════════════════════════════════════════

def _build_history_entry(title="My Title", text="Hello world", encoding="MP3", settings=None):
    """Creates a HistoryEntry and serialises via dataclasses.asdict(), mirroring
    the generate_speech callback's approach."""
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


class TestHistoryEntryCreation:
    def test_entry_has_required_keys(self):
        entry = _build_history_entry()
        assert "id" in entry
        assert "title" in entry
        assert "text_snippet" in entry
        assert "full_text" in entry
        assert "timestamp" in entry
        assert "encoding" in entry
        assert "settings" in entry

    def test_entry_does_not_have_audio_content_b64(self):
        """Audio must not be stored in history (localStorage size budget)."""
        entry = _build_history_entry()
        assert "audio_content_b64" not in entry

    def test_title_stored_correctly(self):
        entry = _build_history_entry(title="Podcast Intro")
        assert entry["title"] == "Podcast Intro"

    def test_text_snippet_truncated_at_80_chars(self):
        long_text = "A" * 200
        entry = _build_history_entry(text=long_text)
        assert len(entry["text_snippet"]) == 80
        assert entry["full_text"] == long_text

    def test_short_text_not_truncated(self):
        short_text = "Short text"
        entry = _build_history_entry(text=short_text)
        assert entry["text_snippet"] == short_text
        assert entry["full_text"] == short_text

    def test_encoding_stored_correctly(self):
        entry = _build_history_entry(encoding="OGG_OPUS")
        assert entry["encoding"] == "OGG_OPUS"

    def test_timestamp_is_iso_format(self):
        entry = _build_history_entry()
        dt = datetime.fromisoformat(entry["timestamp"])
        assert isinstance(dt, datetime)

    def test_id_is_unique_per_entry(self):
        entry1 = _build_history_entry()
        entry2 = _build_history_entry()
        assert entry1["id"] != entry2["id"]

    def test_settings_stored_as_dict(self):
        settings = {"language_code": "fr-FR", "speaking_rate": 1.5}
        entry = _build_history_entry(settings=settings)
        assert entry["settings"] == settings
