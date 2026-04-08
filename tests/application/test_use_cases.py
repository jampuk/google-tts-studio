"""Unit tests for the application use case layer.

All tests use mock ITTSPort implementations (no real API calls).
The conftest.py fixtures provide shared factories for TTSResult, voices, etc.
"""
import pytest
from unittest.mock import MagicMock

from src.application.use_cases.fetch_voices import FetchVoicesUseCase
from src.application.use_cases.preview_voice import PreviewVoiceUseCase
from src.application.use_cases.generate_speech import GenerateSpeechUseCase
from src.domain.models import TTSResult, InputMode, AudioEncoding
from tests.conftest import make_mock_tts_adapter, SAMPLE_VOICES


# ══════════════════════════════════════════════
# FetchVoicesUseCase
# ══════════════════════════════════════════════

class TestFetchVoicesUseCase:
    def test_returns_voices_from_adapter(self):
        adapter = make_mock_tts_adapter(voices=SAMPLE_VOICES)
        uc = FetchVoicesUseCase(adapter)
        voices = uc.execute(api_key="valid-key")
        assert voices == SAMPLE_VOICES

    def test_calls_adapter_list_voices_once(self):
        adapter = make_mock_tts_adapter()
        uc = FetchVoicesUseCase(adapter)
        uc.execute(api_key="valid-key")
        adapter.list_voices.assert_called_once_with(api_key="valid-key")

    def test_strips_whitespace_from_api_key(self):
        adapter = make_mock_tts_adapter()
        uc = FetchVoicesUseCase(adapter)
        uc.execute(api_key="  valid-key  ")
        adapter.list_voices.assert_called_once_with(api_key="valid-key")

    def test_raises_value_error_for_empty_api_key(self):
        uc = FetchVoicesUseCase(make_mock_tts_adapter())
        with pytest.raises(ValueError, match="API key"):
            uc.execute(api_key="")

    def test_raises_value_error_for_whitespace_api_key(self):
        uc = FetchVoicesUseCase(make_mock_tts_adapter())
        with pytest.raises(ValueError, match="API key"):
            uc.execute(api_key="   ")

    def test_propagates_adapter_exception(self):
        adapter = make_mock_tts_adapter()
        adapter.list_voices.side_effect = ValueError("API quota exceeded.")
        uc = FetchVoicesUseCase(adapter)
        with pytest.raises(ValueError, match="quota"):
            uc.execute(api_key="key")

    def test_returns_empty_list_when_adapter_returns_empty(self):
        adapter = make_mock_tts_adapter(voices=[])
        uc = FetchVoicesUseCase(adapter)
        result = uc.execute(api_key="key")
        assert result == []


# ══════════════════════════════════════════════
# PreviewVoiceUseCase
# ══════════════════════════════════════════════

class TestPreviewVoiceUseCase:
    def _make_uc(self, audio_b64="dGVzdA=="):
        adapter = make_mock_tts_adapter(audio_b64=audio_b64)
        return PreviewVoiceUseCase(adapter), adapter

    def test_returns_base64_audio(self):
        uc, _ = self._make_uc(audio_b64="dGVzdA==")
        result = uc.execute(
            voice_name="en-US-Neural2-C",
            language_code="en-US",
            ssml_gender="FEMALE",
            api_key="key",
        )
        assert result == "dGVzdA=="

    def test_uses_mp3_encoding_for_preview(self):
        uc, adapter = self._make_uc()
        uc.execute(
            voice_name="en-US-Neural2-C",
            language_code="en-US",
            ssml_gender="FEMALE",
            api_key="key",
        )
        request = adapter.synthesize.call_args[0][0]
        assert request.settings.audio_encoding == AudioEncoding.MP3

    def test_uses_text_input_mode_for_preview(self):
        uc, adapter = self._make_uc()
        uc.execute(
            voice_name="en-US-Neural2-C",
            language_code="en-US",
            ssml_gender="FEMALE",
            api_key="key",
        )
        request = adapter.synthesize.call_args[0][0]
        assert request.settings.input_mode == InputMode.TEXT

    def test_english_preview_phrase_for_en_us(self):
        uc, adapter = self._make_uc()
        uc.execute(
            voice_name="en-US-Neural2-C",
            language_code="en-US",
            ssml_gender="NEUTRAL",
            api_key="key",
        )
        request = adapter.synthesize.call_args[0][0]
        assert "fox" in request.text.lower()

    def test_french_preview_phrase_for_fr_fr(self):
        uc, adapter = self._make_uc()
        uc.execute(
            voice_name="fr-FR-Neural2-A",
            language_code="fr-FR",
            ssml_gender="FEMALE",
            api_key="key",
        )
        request = adapter.synthesize.call_args[0][0]
        # French phrase contains "renard" (fox in French)
        assert "renard" in request.text.lower()

    def test_falls_back_to_english_for_unknown_language(self):
        uc, adapter = self._make_uc()
        uc.execute(
            voice_name="xx-XX-Standard-A",
            language_code="xx-XX",
            ssml_gender="NEUTRAL",
            api_key="key",
        )
        request = adapter.synthesize.call_args[0][0]
        assert "fox" in request.text.lower()

    def test_raises_for_empty_api_key(self):
        uc, _ = self._make_uc()
        with pytest.raises(ValueError, match="API key"):
            uc.execute(
                voice_name="en-US-Neural2-C",
                language_code="en-US",
                ssml_gender="FEMALE",
                api_key="",
            )

    def test_raises_for_missing_voice_name(self):
        uc, _ = self._make_uc()
        with pytest.raises(ValueError, match="voice_name"):
            uc.execute(
                voice_name="",
                language_code="en-US",
                ssml_gender="FEMALE",
                api_key="key",
            )

    def test_normalises_all_gender_to_neutral(self):
        uc, adapter = self._make_uc()
        uc.execute(
            voice_name="en-US-Neural2-C",
            language_code="en-US",
            ssml_gender="ALL",
            api_key="key",
        )
        request = adapter.synthesize.call_args[0][0]
        assert request.settings.ssml_gender == "NEUTRAL"


# ══════════════════════════════════════════════
# GenerateSpeechUseCase
# ══════════════════════════════════════════════

def _run(adapter=None, **overrides):
    """Helper that invokes GenerateSpeechUseCase.execute() with sensible defaults."""
    if adapter is None:
        adapter = make_mock_tts_adapter()
    uc = GenerateSpeechUseCase(adapter)
    defaults = dict(
        text="Hello world",
        language_code="en-US",
        voice_name="en-US-Neural2-C",
        ssml_gender="NEUTRAL",
        audio_encoding="MP3",
        speaking_rate=1.0,
        pitch=0.0,
        volume_gain_db=0.0,
        effects_profile_id=None,
        input_mode_value="text",
        api_key="valid-key",
        title="My Title",
        history=[],
    )
    defaults.update(overrides)
    return uc.execute(**defaults)


class TestGenerateSpeechUseCase:
    # ── Success path ─────────────────────────────────────────────────────────

    def test_returns_generate_speech_result(self):
        result = _run()
        assert result.audio_content_b64 == "dGVzdGF1ZGlv"
        assert result.encoding == "MP3"
        assert result.character_count == 11

    def test_was_sanitized_false_for_plain_text(self):
        result = _run(text="Hello world")
        assert result.was_sanitized is False

    def test_was_sanitized_true_for_markdown(self):
        result = _run(text="# Hello world")
        # "# Hello world" → "Hello world" after sanitization
        assert result.was_sanitized is True

    def test_clean_text_returned(self):
        result = _run(text="**Hello** world")
        assert result.clean_text == "Hello world"

    def test_safe_title_uses_provided_title(self):
        result = _run(title="My Podcast")
        assert result.safe_title == "My Podcast"

    def test_safe_title_auto_generated_when_empty(self):
        result = _run(title="")
        assert result.safe_title.startswith("tts_")

    def test_history_entry_prepended(self):
        existing = [{"id": "old-id", "title": "old"}]
        result = _run(history=existing)
        assert result.history[0]["title"] == "My Title"
        assert result.history[1]["id"] == "old-id"

    def test_history_capped_at_50(self):
        big_history = [{"id": str(i)} for i in range(50)]
        result = _run(history=big_history)
        assert len(result.history) == 50

    def test_history_entry_has_no_audio_content(self):
        result = _run()
        assert "audio_content_b64" not in result.history[0]

    def test_history_entry_stores_input_mode(self):
        result = _run(input_mode_value="text")
        assert result.history[0]["settings"]["input_mode"] == "text"

    # ── SSML path ────────────────────────────────────────────────────────────

    def test_ssml_mode_preserves_markup(self):
        adapter = make_mock_tts_adapter()
        uc = GenerateSpeechUseCase(adapter)
        ssml = "<speak>Hello <break time='500ms'/></speak>"
        uc.execute(
            text=ssml,
            language_code="en-US",
            voice_name="en-US-Neural2-C",
            ssml_gender="NEUTRAL",
            audio_encoding="MP3",
            speaking_rate=1.0, pitch=0.0, volume_gain_db=0.0,
            effects_profile_id=None,
            input_mode_value="ssml",
            api_key="key",
            title="",
            history=[],
        )
        request = adapter.synthesize.call_args[0][0]
        assert request.text == ssml.strip()
        assert request.settings.input_mode == InputMode.SSML

    def test_ssml_invalid_xml_raises_value_error(self):
        with pytest.raises(ValueError, match="XML"):
            _run(
                text="<speak>Unclosed",
                input_mode_value="ssml",
            )

    def test_ssml_wrong_root_element_raises_value_error(self):
        with pytest.raises(ValueError, match="<speak>"):
            _run(
                text="<div>Hello</div>",
                input_mode_value="ssml",
            )

    # ── Validation failures ───────────────────────────────────────────────────

    def test_empty_text_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            _run(text="")

    def test_whitespace_only_text_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            _run(text="   ")

    def test_empty_api_key_raises_value_error(self):
        with pytest.raises(ValueError, match="API key"):
            _run(api_key="")

    def test_text_only_html_empty_after_clean_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            _run(text="<p>   </p>")

    def test_text_exceeding_5000_bytes_raises_value_error(self):
        with pytest.raises(ValueError, match="5000"):
            _run(text="a" * 5001)

    def test_multibyte_text_exceeding_5000_bytes_raises_value_error(self):
        # Each CJK character = 3 bytes; 1668 chars = 5004 bytes
        with pytest.raises(ValueError, match="5000"):
            _run(text="日" * 1668)

    def test_missing_language_code_raises_value_error(self):
        with pytest.raises(ValueError, match="Language"):
            _run(language_code="")

    def test_missing_voice_name_raises_value_error(self):
        with pytest.raises(ValueError, match="Language"):
            _run(voice_name="")

    # ── Adapter error propagation ─────────────────────────────────────────────

    def test_adapter_value_error_propagates(self):
        adapter = make_mock_tts_adapter()
        adapter.synthesize.side_effect = ValueError("Google API error (HTTP 403)")
        with pytest.raises(ValueError, match="403"):
            _run(adapter=adapter)

    # ── ALL gender normalisation ──────────────────────────────────────────────

    def test_all_gender_normalised_to_neutral(self):
        adapter = make_mock_tts_adapter()
        _run(adapter=adapter, ssml_gender="ALL")
        request = adapter.synthesize.call_args[0][0]
        assert request.settings.ssml_gender == "NEUTRAL"
