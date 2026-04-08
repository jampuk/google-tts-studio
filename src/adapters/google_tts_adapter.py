import logging
import requests
from typing import Optional

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.domain.models import TTSRequest, TTSResult, InputMode
from src.ports.tts_port import ITTSPort

logger = logging.getLogger(__name__)

GOOGLE_TTS_API_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
GOOGLE_VOICES_API_URL = "https://texttospeech.googleapis.com/v1/voices"

# HTTP status codes that are transient and safe to retry.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient failures that should trigger a retry.

    Retries on:
    - requests.Timeout — network-level timeout
    - requests.ConnectionError — DNS / TCP-level failure
    - _RetryableAPIError — HTTP 429 / 5xx responses (raised explicitly below)
    """
    return isinstance(exc, (requests.Timeout, requests.ConnectionError, _RetryableAPIError))


class _RetryableAPIError(Exception):
    """Raised internally when a retryable HTTP status code is received.

    This is caught by tenacity's retry predicate and retried with backoff.
    After all attempts are exhausted tenacity re-raises it, at which point
    the caller converts it to a ValueError for the application layer.
    """
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"HTTP {status}: {message}")


def _retry_decorator():
    """Return a tenacity @retry decorator configured for Google TTS API calls.

    Strategy:
      - Up to 3 attempts total (1 initial + 2 retries)
      - Exponential backoff: 1 s → 2 s → 4 s (capped at 10 s)
      - Only retries _RetryableAPIError, requests.Timeout, ConnectionError
    """
    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class GoogleTTSAdapter(ITTSPort):
    """Adapter that calls the Google Cloud TTS REST API.

    Implements automatic retry with exponential backoff for transient errors
    (timeouts, connection errors, HTTP 429/5xx).  Non-retryable errors (4xx
    other than 429) are surfaced immediately as ValueError.
    """

    @_retry_decorator()
    def list_voices(self, api_key: str, language_code: Optional[str] = None) -> list:
        """Fetch the full list of available voices from the Google TTS API.

        Translates camelCase API response fields into snake_case dicts
        for internal use. Raises ValueError on non-200 responses.

        The API key is sent via the X-Goog-Api-Key header (not a URL query
        parameter) to keep it out of server access logs and browser history.
        """
        logger.info("Fetching voice list (language_code=%s)", language_code or "all")

        params = {}
        if language_code:
            params["languageCode"] = language_code

        response = requests.get(
            GOOGLE_VOICES_API_URL,
            params=params or None,
            headers={"X-Goog-Api-Key": api_key},
            timeout=15,
        )

        if response.status_code != 200:
            try:
                error_detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                error_detail = response.text
            logger.error("Voice fetch failed (HTTP %s): %s", response.status_code, error_detail)
            if response.status_code in _RETRYABLE_STATUS_CODES:
                raise _RetryableAPIError(response.status_code, error_detail)
            raise ValueError(
                f"Google TTS list voices error (HTTP {response.status_code}): {error_detail}"
            )

        raw_voices = response.json().get("voices", [])

        # Translate camelCase API fields → snake_case for internal use
        voices = []
        for v in raw_voices:
            voices.append({
                "name": v.get("name", ""),
                "language_codes": v.get("languageCodes", []),
                "ssml_gender": v.get("ssmlGender", "NEUTRAL"),
                "natural_sample_rate_hertz": v.get("naturalSampleRateHertz", 0),
            })

        logger.info("Fetched %d voices", len(voices))
        return voices

    @_retry_decorator()
    def synthesize(self, request: TTSRequest) -> TTSResult:
        settings = request.settings

        logger.info(
            "Synthesising: mode=%s, chars=%d, voice=%s, encoding=%s",
            settings.input_mode,
            len(request.text),
            settings.voice_name,
            settings.audio_encoding,
        )

        audio_config = {
            "audioEncoding": settings.audio_encoding,
            "speakingRate": settings.speaking_rate,
            "pitch": settings.pitch,
            "volumeGainDb": settings.volume_gain_db,
        }

        if settings.effects_profile_id:
            audio_config["effectsProfileId"] = [settings.effects_profile_id]

        # Use "ssml" key when SSML mode is active, otherwise "text".
        input_key = "ssml" if settings.input_mode == InputMode.SSML else "text"

        payload = {
            "input": {input_key: request.text},
            "voice": {
                "languageCode": settings.language_code,
                "name": settings.voice_name,
                "ssmlGender": settings.ssml_gender,
            },
            "audioConfig": audio_config,
        }

        # API key sent via header — keeps it out of server logs and browser history.
        response = requests.post(
            GOOGLE_TTS_API_URL,
            headers={"X-Goog-Api-Key": request.api_key},
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            try:
                error_detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                error_detail = response.text
            logger.error("Synthesis failed (HTTP %s): %s", response.status_code, error_detail)
            if response.status_code in _RETRYABLE_STATUS_CODES:
                raise _RetryableAPIError(response.status_code, error_detail)
            raise ValueError(
                f"Google TTS API error (HTTP {response.status_code}): {error_detail}"
            )

        data = response.json()
        audio_content_b64 = data.get("audioContent", "")

        logger.info(
            "Synthesis succeeded: voice=%s, chars=%d",
            settings.voice_name,
            len(request.text),
        )

        return TTSResult(
            audio_content_b64=audio_content_b64,
            encoding=settings.audio_encoding,
            character_count=len(request.text),
        )
