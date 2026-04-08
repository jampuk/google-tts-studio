import pytest
from src.domain.models import (
    AudioEncoding,
    InputMode,
    TTSSettings,
    TTSRequest,
    TTSResult,
    HistoryEntry,
    sanitize_text,
    utf8_byte_length,
    validate_ssml,
    get_preview_phrase,
    PREVIEW_PHRASES,
)


# ══════════════════════════════════════════════
# AudioEncoding
# ══════════════════════════════════════════════

class TestAudioEncoding:
    def test_mp3_value(self):
        assert AudioEncoding.MP3 == "MP3"

    def test_linear16_value(self):
        assert AudioEncoding.LINEAR16 == "LINEAR16"

    def test_ogg_opus_value(self):
        assert AudioEncoding.OGG_OPUS == "OGG_OPUS"

    def test_mulaw_value(self):
        assert AudioEncoding.MULAW == "MULAW"

    def test_alaw_value(self):
        assert AudioEncoding.ALAW == "ALAW"

    def test_is_string_enum(self):
        assert isinstance(AudioEncoding.MP3, str)

    def test_all_members(self):
        members = [e.value for e in AudioEncoding]
        assert "MP3" in members
        assert "LINEAR16" in members
        assert "OGG_OPUS" in members
        assert "MULAW" in members
        assert "ALAW" in members

    # ── .mime attribute ──────────────────────────────────────────────────────

    def test_mp3_mime(self):
        assert AudioEncoding.MP3.mime == "audio/mpeg"

    def test_linear16_mime(self):
        assert AudioEncoding.LINEAR16.mime == "audio/wav"

    def test_ogg_opus_mime(self):
        assert AudioEncoding.OGG_OPUS.mime == "audio/ogg"

    def test_mulaw_mime(self):
        assert AudioEncoding.MULAW.mime == "audio/basic"

    def test_alaw_mime(self):
        assert AudioEncoding.ALAW.mime == "audio/pcm"

    # ── .ext attribute ───────────────────────────────────────────────────────

    def test_mp3_ext(self):
        assert AudioEncoding.MP3.ext == ".mp3"

    def test_linear16_ext(self):
        assert AudioEncoding.LINEAR16.ext == ".wav"

    def test_ogg_opus_ext(self):
        assert AudioEncoding.OGG_OPUS.ext == ".ogg"

    def test_mulaw_ext(self):
        assert AudioEncoding.MULAW.ext == ".au"

    def test_alaw_ext(self):
        assert AudioEncoding.ALAW.ext == ".alaw"

    def test_all_ext_start_with_dot(self):
        for member in AudioEncoding:
            assert member.ext.startswith("."), f"{member} ext must start with '.'"

    # ── from_str() ───────────────────────────────────────────────────────────

    def test_from_str_mp3(self):
        assert AudioEncoding.from_str("MP3") == AudioEncoding.MP3

    def test_from_str_ogg_opus(self):
        assert AudioEncoding.from_str("OGG_OPUS") == AudioEncoding.OGG_OPUS

    def test_from_str_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown audio encoding"):
            AudioEncoding.from_str("INVALID")


# ══════════════════════════════════════════════
# InputMode
# ══════════════════════════════════════════════

class TestInputMode:
    def test_text_value(self):
        assert InputMode.TEXT == "text"

    def test_ssml_value(self):
        assert InputMode.SSML == "ssml"

    def test_is_string_enum(self):
        assert isinstance(InputMode.TEXT, str)
        assert isinstance(InputMode.SSML, str)

    def test_all_members_present(self):
        members = [m.value for m in InputMode]
        assert "text" in members
        assert "ssml" in members

    def test_can_construct_from_string(self):
        assert InputMode("text") == InputMode.TEXT
        assert InputMode("ssml") == InputMode.SSML

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            InputMode("html")


# ══════════════════════════════════════════════
# utf8_byte_length
# ══════════════════════════════════════════════

class TestUtf8ByteLength:
    def test_empty_string(self):
        assert utf8_byte_length("") == 0

    def test_ascii_text_bytes_equal_chars(self):
        text = "Hello, world!"
        assert utf8_byte_length(text) == len(text)

    def test_multibyte_cjk(self):
        # Each CJK character is 3 UTF-8 bytes
        text = "日本語"
        assert utf8_byte_length(text) == 9
        assert len(text) == 3

    def test_multibyte_arabic(self):
        # Arabic characters are 2 bytes each in UTF-8
        text = "مرحبا"
        assert utf8_byte_length(text) > len(text)

    def test_mixed_ascii_and_cjk(self):
        # "Hi" (2 bytes) + "日" (3 bytes) = 5 bytes
        text = "Hi日"
        assert utf8_byte_length(text) == 5
        assert len(text) == 3

    def test_exactly_5000_ascii_bytes(self):
        text = "a" * 5000
        assert utf8_byte_length(text) == 5000

    def test_emoji_is_4_bytes(self):
        # U+1F600 GRINNING FACE encodes to 4 bytes in UTF-8
        assert utf8_byte_length("😀") == 4
        assert len("😀") == 1

    def test_newline_is_1_byte(self):
        assert utf8_byte_length("\n") == 1

    def test_returns_int(self):
        assert isinstance(utf8_byte_length("test"), int)


# ══════════════════════════════════════════════
# sanitize_text
# ══════════════════════════════════════════════

class TestSanitizeText:
    def test_empty_string_returns_empty(self):
        assert sanitize_text("") == ""

    def test_plain_text_unchanged(self):
        text = "Hello, this is plain text."
        assert sanitize_text(text) == text

    def test_strips_fenced_code_blocks(self):
        text = "Before\n```python\ncode here\n```\nAfter"
        result = sanitize_text(text)
        assert "```" not in result
        assert "code here" not in result
        assert "Before" in result
        assert "After" in result

    def test_strips_inline_code(self):
        result = sanitize_text("Use `print()` function")
        assert "`" not in result
        assert "print()" not in result
        assert "Use" in result
        assert "function" in result

    def test_strips_atx_headings(self):
        result = sanitize_text("# Heading 1\n## Heading 2\nBody")
        assert "#" not in result
        assert "Heading 1" in result
        assert "Heading 2" in result
        assert "Body" in result

    def test_strips_setext_underlines(self):
        text = "Heading\n=======\nSubheading\n-------\nBody"
        result = sanitize_text(text)
        assert "=======" not in result
        assert "-------" not in result
        assert "Heading" in result
        assert "Body" in result

    def test_strips_blockquotes(self):
        result = sanitize_text("> This is a quote\n> Second line")
        assert ">" not in result
        assert "This is a quote" in result

    def test_strips_unordered_list_markers(self):
        text = "- Item one\n* Item two\n+ Item three"
        result = sanitize_text(text)
        assert "Item one" in result
        assert "Item two" in result
        assert "Item three" in result
        # Markers removed at line start (content preserved)
        for line in result.splitlines():
            assert not line.startswith("-")
            assert not line.startswith("*")
            assert not line.startswith("+")

    def test_strips_ordered_list_markers(self):
        text = "1. First\n2. Second\n10. Tenth"
        result = sanitize_text(text)
        assert "First" in result
        assert "Second" in result
        assert "Tenth" in result

    def test_strips_bold_double_asterisk(self):
        result = sanitize_text("This is **bold** text")
        assert "**" not in result
        assert "bold" in result

    def test_strips_bold_double_underscore(self):
        result = sanitize_text("This is __bold__ text")
        assert "__" not in result
        assert "bold" in result

    def test_strips_italic_asterisk(self):
        result = sanitize_text("This is *italic* text")
        assert sanitize_text("*italic*") == "italic"

    def test_strips_italic_underscore(self):
        assert sanitize_text("_italic_") == "italic"

    def test_strips_bold_italic(self):
        result = sanitize_text("***bold italic***")
        assert "***" not in result
        assert "bold italic" in result

    def test_strips_markdown_links_keeps_text(self):
        result = sanitize_text("[Click here](https://example.com)")
        assert "Click here" in result
        assert "https://example.com" not in result
        assert "[" not in result
        assert "]" not in result

    def test_strips_markdown_images_keeps_alt(self):
        result = sanitize_text("![Alt text](image.png)")
        assert "Alt text" in result
        assert "image.png" not in result

    def test_strips_bare_urls(self):
        result = sanitize_text("Visit https://example.com for more")
        assert "https://example.com" not in result
        assert "Visit" in result
        assert "for more" in result

    def test_strips_html_tags(self):
        result = sanitize_text("<p>Hello</p> <b>world</b>")
        assert "<p>" not in result
        assert "</p>" not in result
        assert "<b>" not in result
        assert "Hello" in result
        assert "world" in result

    def test_decodes_html_entities(self):
        result = sanitize_text("Tom &amp; Jerry")
        assert "&amp;" not in result
        assert "Tom & Jerry" == result

    def test_collapses_multiple_blank_lines(self):
        text = "First\n\n\n\nSecond"
        result = sanitize_text(text)
        assert "\n\n\n" not in result
        assert "First" in result
        assert "Second" in result

    def test_collapses_multiple_spaces(self):
        result = sanitize_text("Hello    world")
        assert "  " not in result
        assert "Hello world" == result

    def test_strips_leading_trailing_whitespace(self):
        result = sanitize_text("  Hello world  ")
        assert result == "Hello world"

    def test_complex_markdown_document(self):
        text = (
            "# Title\n\n"
            "Some **bold** and *italic* text with a [link](http://example.com).\n\n"
            "```python\ndef foo(): pass\n```\n\n"
            "- Item 1\n- Item 2\n"
        )
        result = sanitize_text(text)
        assert "#" not in result
        assert "**" not in result
        assert "[link]" not in result
        assert "```" not in result
        assert "def foo" not in result
        assert "Title" in result
        assert "bold" in result
        assert "italic" in result
        assert "Item 1" in result


# ══════════════════════════════════════════════
# TTSSettings
# ══════════════════════════════════════════════

class TestTTSSettings:
    def test_defaults(self):
        settings = TTSSettings()
        assert settings.language_code == "en-US"
        assert settings.voice_name == "en-US-Neural2-C"
        assert settings.ssml_gender == "NEUTRAL"
        assert settings.audio_encoding == AudioEncoding.MP3
        assert settings.speaking_rate == 1.0
        assert settings.pitch == 0.0
        assert settings.volume_gain_db == 0.0
        assert settings.effects_profile_id is None

    def test_default_input_mode_is_text(self):
        settings = TTSSettings()
        assert settings.input_mode == InputMode.TEXT

    def test_custom_input_mode_ssml(self):
        settings = TTSSettings(input_mode=InputMode.SSML)
        assert settings.input_mode == InputMode.SSML

    def test_audio_encoding_annotation_is_audio_encoding_type(self):
        settings = TTSSettings()
        # audio_encoding default must be an AudioEncoding instance (not a bare string)
        assert isinstance(settings.audio_encoding, AudioEncoding)

    def test_custom_values(self):
        settings = TTSSettings(
            language_code="fr-FR",
            voice_name="fr-FR-Neural2-A",
            ssml_gender="FEMALE",
            audio_encoding=AudioEncoding.OGG_OPUS,
            speaking_rate=1.5,
            pitch=2.0,
            volume_gain_db=-3.0,
            effects_profile_id="headphone-class-device",
        )
        assert settings.language_code == "fr-FR"
        assert settings.voice_name == "fr-FR-Neural2-A"
        assert settings.ssml_gender == "FEMALE"
        assert settings.audio_encoding == AudioEncoding.OGG_OPUS
        assert settings.speaking_rate == 1.5
        assert settings.pitch == 2.0
        assert settings.volume_gain_db == -3.0
        assert settings.effects_profile_id == "headphone-class-device"


# ══════════════════════════════════════════════
# TTSRequest
# ══════════════════════════════════════════════

class TestTTSRequest:
    def test_instantiation(self):
        settings = TTSSettings()
        request = TTSRequest(
            text="Hello, world!",
            settings=settings,
            api_key="test-api-key-123",
        )
        assert request.text == "Hello, world!"
        assert request.settings is settings
        assert request.api_key == "test-api-key-123"

    def test_text_stored_correctly(self):
        settings = TTSSettings()
        long_text = "A" * 4999
        request = TTSRequest(text=long_text, settings=settings, api_key="key")
        assert request.text == long_text
        assert len(request.text) == 4999


# ══════════════════════════════════════════════
# TTSResult
# ══════════════════════════════════════════════

class TestTTSResult:
    def test_instantiation(self):
        result = TTSResult(
            audio_content_b64="dGVzdA==",
            encoding="MP3",
            character_count=42,
        )
        assert result.audio_content_b64 == "dGVzdA=="
        assert result.encoding == "MP3"
        assert result.character_count == 42

    def test_zero_character_count(self):
        result = TTSResult(audio_content_b64="", encoding="LINEAR16", character_count=0)
        assert result.character_count == 0


# ══════════════════════════════════════════════
# HistoryEntry
# ══════════════════════════════════════════════

class TestHistoryEntry:
    def _make_entry(self, **kwargs):
        defaults = dict(
            id="abc-123",
            title="My Recording",
            text_snippet="Hello world",
            full_text="Hello world, this is a test.",
            timestamp="2024-01-01T00:00:00+00:00",
            encoding="MP3",
            settings={"language_code": "en-US", "voice_name": "en-US-Neural2-C"},
        )
        defaults.update(kwargs)
        return HistoryEntry(**defaults)

    def test_instantiation_with_all_fields(self):
        entry = self._make_entry()
        assert entry.id == "abc-123"
        assert entry.title == "My Recording"
        assert entry.text_snippet == "Hello world"
        assert entry.full_text == "Hello world, this is a test."
        assert entry.timestamp == "2024-01-01T00:00:00+00:00"
        assert entry.encoding == "MP3"
        assert entry.settings["language_code"] == "en-US"

    def test_audio_content_b64_not_a_field(self):
        """audio is intentionally excluded from history to keep localStorage small."""
        entry = self._make_entry()
        assert not hasattr(entry, "audio_content_b64")

    def test_title_stored_correctly(self):
        entry = self._make_entry(title="Podcast intro")
        assert entry.title == "Podcast intro"

    def test_settings_is_dict(self):
        entry = self._make_entry(settings={"speaking_rate": 1.5, "pitch": 0.0})
        assert isinstance(entry.settings, dict)
        assert entry.settings["speaking_rate"] == 1.5

    def test_different_encoding(self):
        entry = self._make_entry(encoding="OGG_OPUS")
        assert entry.encoding == "OGG_OPUS"


# ══════════════════════════════════════════════
# validate_ssml
# ══════════════════════════════════════════════

class TestValidateSsml:
    def test_valid_speak_root_passes(self):
        validate_ssml("<speak>Hello world</speak>")  # must not raise

    def test_valid_speak_with_tags_passes(self):
        validate_ssml(
            "<speak>Hello <break time='500ms'/> world</speak>"
        )  # must not raise

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            validate_ssml("")

    def test_whitespace_only_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            validate_ssml("   ")

    def test_malformed_xml_raises_value_error(self):
        with pytest.raises(ValueError, match="XML"):
            validate_ssml("<speak>Unclosed")

    def test_wrong_root_element_raises_value_error(self):
        with pytest.raises(ValueError, match="<speak>"):
            validate_ssml("<div>Hello</div>")

    def test_plain_text_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_ssml("Just plain text")


# ══════════════════════════════════════════════
# get_preview_phrase / PREVIEW_PHRASES
# ══════════════════════════════════════════════

class TestPreviewPhrases:
    def test_english_phrase_for_en_us(self):
        phrase = get_preview_phrase("en-US")
        assert phrase == PREVIEW_PHRASES["en"]

    def test_french_phrase_for_fr_fr(self):
        phrase = get_preview_phrase("fr-FR")
        assert phrase == PREVIEW_PHRASES["fr"]

    def test_german_phrase_for_de_de(self):
        phrase = get_preview_phrase("de-DE")
        assert phrase == PREVIEW_PHRASES["de"]

    def test_japanese_phrase_for_ja_jp(self):
        phrase = get_preview_phrase("ja-JP")
        assert phrase == PREVIEW_PHRASES["ja"]

    def test_falls_back_to_english_for_unknown_language(self):
        phrase = get_preview_phrase("xx-XX")
        assert phrase == PREVIEW_PHRASES["en"]

    def test_falls_back_to_english_for_empty_string(self):
        phrase = get_preview_phrase("")
        assert phrase == PREVIEW_PHRASES["en"]

    def test_preview_phrases_dict_has_english_key(self):
        assert "en" in PREVIEW_PHRASES

    def test_all_phrases_are_non_empty_strings(self):
        for lang, phrase in PREVIEW_PHRASES.items():
            assert isinstance(phrase, str) and phrase.strip(), \
                f"Phrase for '{lang}' must be a non-empty string"


# ══════════════════════════════════════════════
# TTSSettings — __post_init__ validation
# ══════════════════════════════════════════════

class TestTTSSettingsValidation:
    def test_valid_defaults_pass(self):
        TTSSettings()  # must not raise

    def test_speaking_rate_too_low_raises(self):
        with pytest.raises(ValueError, match="speaking_rate"):
            TTSSettings(speaking_rate=0.0)

    def test_speaking_rate_too_high_raises(self):
        with pytest.raises(ValueError, match="speaking_rate"):
            TTSSettings(speaking_rate=5.0)

    def test_speaking_rate_at_min_boundary_passes(self):
        TTSSettings(speaking_rate=0.25)  # must not raise

    def test_speaking_rate_at_max_boundary_passes(self):
        TTSSettings(speaking_rate=4.0)  # must not raise

    def test_pitch_too_low_raises(self):
        with pytest.raises(ValueError, match="pitch"):
            TTSSettings(pitch=-21.0)

    def test_pitch_too_high_raises(self):
        with pytest.raises(ValueError, match="pitch"):
            TTSSettings(pitch=21.0)

    def test_pitch_at_boundaries_passes(self):
        TTSSettings(pitch=-20.0)  # must not raise
        TTSSettings(pitch=20.0)  # must not raise

    def test_volume_gain_too_low_raises(self):
        with pytest.raises(ValueError, match="volume_gain_db"):
            TTSSettings(volume_gain_db=-97.0)

    def test_volume_gain_too_high_raises(self):
        with pytest.raises(ValueError, match="volume_gain_db"):
            TTSSettings(volume_gain_db=17.0)

    def test_volume_gain_at_boundaries_passes(self):
        TTSSettings(volume_gain_db=-96.0)  # must not raise
        TTSSettings(volume_gain_db=16.0)   # must not raise

    def test_empty_language_code_raises(self):
        with pytest.raises(ValueError, match="language_code"):
            TTSSettings(language_code="")

    def test_whitespace_language_code_raises(self):
        with pytest.raises(ValueError, match="language_code"):
            TTSSettings(language_code="   ")

    def test_empty_voice_name_raises(self):
        with pytest.raises(ValueError, match="voice_name"):
            TTSSettings(voice_name="")
