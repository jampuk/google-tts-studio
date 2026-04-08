import logging
from src.domain.models import (
    TTSRequest,
    TTSSettings,
    InputMode,
    AudioEncoding,
    get_preview_phrase,
)
from src.ports.tts_port import ITTSPort

logger = logging.getLogger(__name__)


class PreviewVoiceUseCase:
    """Synthesises a short language-appropriate phrase to audition a voice.

    Uses a curated language-aware phrase (see ``domain.models.PREVIEW_PHRASES``)
    so that non-English voices are previewed with meaningful content rather than
    an always-English sentence.
    """

    def __init__(self, tts_port: ITTSPort) -> None:
        self._port = tts_port

    def execute(
        self,
        voice_name: str,
        language_code: str,
        ssml_gender: str,
        api_key: str,
    ) -> str:
        """Synthesise a preview phrase and return the base64-encoded MP3 audio.

        Args:
            voice_name: The fully-qualified voice name (e.g. "en-US-Neural2-C").
            language_code: BCP-47 language code (e.g. "en-US").
            ssml_gender: SSML gender string (e.g. "FEMALE", "MALE", "NEUTRAL").
            api_key: A non-empty Google Cloud API key.

        Returns:
            Base64-encoded MP3 audio string suitable for embedding in a data URI.

        Raises:
            ValueError: If any required argument is missing or the adapter call
                fails after all retries are exhausted.
        """
        key = (api_key or "").strip()
        if not key:
            raise ValueError("API key must not be empty.")
        if not voice_name or not language_code:
            raise ValueError("voice_name and language_code are required.")

        phrase = get_preview_phrase(language_code)
        api_gender = ssml_gender if ssml_gender and ssml_gender != "ALL" else "NEUTRAL"

        logger.info(
            "PreviewVoiceUseCase: voice=%s, language=%s, phrase=%r",
            voice_name,
            language_code,
            phrase[:40],
        )

        settings = TTSSettings(
            language_code=language_code,
            voice_name=voice_name,
            ssml_gender=api_gender,
            audio_encoding=AudioEncoding.MP3,
            input_mode=InputMode.TEXT,
        )
        request = TTSRequest(text=phrase, settings=settings, api_key=key)
        result = self._port.synthesize(request)
        return result.audio_content_b64
