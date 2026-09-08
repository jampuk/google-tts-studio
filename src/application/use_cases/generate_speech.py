import dataclasses
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.domain.models import (
    AudioEncoding,
    HistoryEntry,
    InputMode,
    TTSRequest,
    TTSSettings,
    sanitize_text,
    utf8_byte_length,
    validate_ssml,
)
from src.ports.tts_port import ITTSPort

logger = logging.getLogger(__name__)

_MAX_HISTORY = 50
_MAX_BYTE_LIMIT = 5000


class GenerateSpeechResult:
    """Value object returned by GenerateSpeechUseCase.execute()."""

    __slots__ = (
        "audio_content_b64",
        "encoding",
        "character_count",
        "safe_title",
        "clean_text",
        "was_sanitized",
        "history",
    )

    def __init__(
        self,
        audio_content_b64: str,
        encoding: str,
        character_count: int,
        safe_title: str,
        clean_text: str,
        was_sanitized: bool,
        history: list[dict],
    ) -> None:
        self.audio_content_b64 = audio_content_b64
        self.encoding = encoding
        self.character_count = character_count
        self.safe_title = safe_title
        self.clean_text = clean_text
        self.was_sanitized = was_sanitized
        self.history = history


class GenerateSpeechUseCase:
    """Orchestrates the full text-to-speech generation flow.

    Responsibilities:
    - Sanitize plain text (strip HTML/Markdown) or validate SSML XML.
    - Enforce the Google TTS 5 000 UTF-8 byte limit.
    - Build a TTSRequest and call the ITTSPort adapter.
    - Construct a HistoryEntry and prepend it to the history list (capped at 50).

    The callback layer receives a GenerateSpeechResult and is responsible only
    for updating Dash component state — no business logic lives there.
    """

    def __init__(self, tts_port: ITTSPort) -> None:
        self._port = tts_port

    def execute(
        self,
        text: str,
        language_code: str,
        voice_name: str,
        ssml_gender: str,
        audio_encoding: str,
        speaking_rate: float,
        pitch: float,
        volume_gain_db: float,
        effects_profile_id: Optional[str],
        input_mode_value: str,
        api_key: str,
        title: Optional[str],
        history: list[dict],
        bypass_cleanup: bool = False,
    ) -> GenerateSpeechResult:
        """Run the full TTS generation flow.

        Args:
            text: Raw user-entered text (plain or SSML).
            language_code: BCP-47 language code.
            voice_name: Fully-qualified Google voice name.
            ssml_gender: "MALE", "FEMALE", "NEUTRAL", or "ALL".
            audio_encoding: Encoding string e.g. "MP3".
            speaking_rate: 0.25 – 4.0.
            pitch: -20.0 – 20.0.
            volume_gain_db: -96.0 – 16.0.
            effects_profile_id: Optional device effects profile key.
            input_mode_value: "text" or "ssml".
            api_key: Non-empty Google Cloud API key.
            title: Optional user-supplied title (used as download filename).
            history: Current history list (JSON-serialisable dicts).
            bypass_cleanup: When True, skip sanitize_text() and send the raw
                text directly (plain-text mode only; ignored in SSML mode).

        Returns:
            GenerateSpeechResult value object.

        Raises:
            ValueError: For any validation failure or adapter error.
        """
        # ── Guard: required fields ────────────────────────────────────────────
        key = (api_key or "").strip()
        if not key:
            raise ValueError("API key must not be empty. Save your API key first.")

        if not text or not text.strip():
            raise ValueError("Text content is empty. Please enter some text.")

        if not language_code or not voice_name:
            raise ValueError(
                "Language and voice must be selected before generating speech."
            )

        # ── Resolve input mode ────────────────────────────────────────────────
        try:
            mode = InputMode(input_mode_value) if input_mode_value else InputMode.TEXT
        except ValueError:
            mode = InputMode.TEXT

        # ── Text preparation ──────────────────────────────────────────────────
        if mode == InputMode.SSML:
            # Validate XML structure before making an API call.
            validate_ssml(text.strip())
            clean_text = text.strip()
            was_sanitized = False
        elif bypass_cleanup:
            # User opted to skip all cleanup — send raw text as-is.
            clean_text = text.strip()
            if not clean_text:
                raise ValueError(
                    "Text content is empty. Please enter some text."
                )
            was_sanitized = False
        else:
            clean_text = sanitize_text(text)
            if not clean_text:
                raise ValueError(
                    "Text is empty after stripping HTML/Markdown. "
                    "Please enter plain text content."
                )
            was_sanitized = clean_text != text.strip()

        # ── Byte-limit validation ─────────────────────────────────────────────
        byte_count = utf8_byte_length(clean_text)
        if byte_count > _MAX_BYTE_LIMIT:
            raise ValueError(
                f"Text exceeds the {_MAX_BYTE_LIMIT}-byte limit "
                f"({byte_count} bytes after cleaning)."
            )

        # ── Build domain objects ──────────────────────────────────────────────
        api_gender = ssml_gender if ssml_gender and ssml_gender != "ALL" else "NEUTRAL"
        encoding_enum = AudioEncoding.from_str(audio_encoding or "MP3")

        settings = TTSSettings(
            language_code=language_code,
            voice_name=voice_name,
            ssml_gender=api_gender,
            audio_encoding=encoding_enum,
            speaking_rate=speaking_rate if speaking_rate is not None else 1.0,
            pitch=pitch if pitch is not None else 0.0,
            volume_gain_db=volume_gain_db if volume_gain_db is not None else 0.0,
            effects_profile_id=effects_profile_id or None,
            input_mode=mode,
        )
        request = TTSRequest(text=clean_text, settings=settings, api_key=key)

        logger.info(
            "GenerateSpeechUseCase: mode=%s, bytes=%d, voice=%s, encoding=%s",
            mode,
            byte_count,
            voice_name,
            audio_encoding,
        )

        # ── Adapter call ──────────────────────────────────────────────────────
        result = self._port.synthesize(request)

        # ── Title ─────────────────────────────────────────────────────────────
        safe_title = (title or "").strip()
        if not safe_title:
            safe_title = f"tts_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # ── History entry ─────────────────────────────────────────────────────
        history_entry = HistoryEntry(
            id=str(uuid.uuid4()),
            title=safe_title,
            text_snippet=clean_text[:80],
            full_text=clean_text,
            timestamp=datetime.now(timezone.utc).isoformat(),
            encoding=result.encoding,
            settings={
                "language_code": settings.language_code,
                "voice_name": settings.voice_name,
                "ssml_gender": settings.ssml_gender,
                "audio_encoding": settings.audio_encoding,
                "speaking_rate": settings.speaking_rate,
                "pitch": settings.pitch,
                "volume_gain_db": settings.volume_gain_db,
                "effects_profile_id": settings.effects_profile_id,
                "input_mode": settings.input_mode,
            },
        )
        updated_history = [dataclasses.asdict(history_entry)] + list(history or [])
        if len(updated_history) > _MAX_HISTORY:
            updated_history = updated_history[:_MAX_HISTORY]

        logger.info(
            "GenerateSpeechUseCase: succeeded — title=%s, chars=%d, bytes=%d",
            safe_title,
            result.character_count,
            byte_count,
        )

        return GenerateSpeechResult(
            audio_content_b64=result.audio_content_b64,
            encoding=result.encoding,
            character_count=result.character_count,
            safe_title=safe_title,
            clean_text=clean_text,
            was_sanitized=was_sanitized,
            history=updated_history,
        )
