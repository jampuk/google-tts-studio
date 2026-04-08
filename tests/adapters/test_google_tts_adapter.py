import pytest
from unittest.mock import patch, MagicMock, call

from src.adapters.google_tts_adapter import GoogleTTSAdapter, _RetryableAPIError
from src.domain.models import TTSRequest, TTSSettings, TTSResult, InputMode, AudioEncoding


# ──────────────────────────────────────────────
# Fixtures / helpers
# ──────────────────────────────────────────────

def make_request(
    text="Hello world",
    effects_profile_id=None,
    encoding="MP3",
    input_mode=InputMode.TEXT,
):
    settings = TTSSettings(
        language_code="en-US",
        voice_name="en-US-Neural2-C",
        ssml_gender="NEUTRAL",
        audio_encoding=encoding,
        speaking_rate=1.0,
        pitch=0.0,
        volume_gain_db=0.0,
        effects_profile_id=effects_profile_id,
        input_mode=input_mode,
    )
    return TTSRequest(text=text, settings=settings, api_key="fake-api-key")


def _ok_response(audio_b64="dGVzdGF1ZGlv"):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"audioContent": audio_b64}
    return mock


def _err_response(status, message="Something went wrong"):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = {"error": {"message": message}}
    mock.text = message
    return mock


# ══════════════════════════════════════════════
# synthesize()
# ══════════════════════════════════════════════

class TestSynthesize:
    def test_successful_synthesis_returns_tts_result(self):
        with patch("requests.post", return_value=_ok_response("dGVzdGF1ZGlv")):
            result = GoogleTTSAdapter().synthesize(make_request(text="Hello world"))
        assert isinstance(result, TTSResult)
        assert result.audio_content_b64 == "dGVzdGF1ZGlv"
        assert result.encoding == "MP3"
        assert result.character_count == len("Hello world")

    def test_api_call_uses_correct_url(self):
        with patch("requests.post", return_value=_ok_response()) as mock_post:
            GoogleTTSAdapter().synthesize(make_request())
        url = mock_post.call_args[0][0]
        assert "texttospeech.googleapis.com" in url

    def test_api_key_sent_as_header_not_query_param(self):
        """API key must travel in X-Goog-Api-Key header, not the URL."""
        with patch("requests.post", return_value=_ok_response()) as mock_post:
            GoogleTTSAdapter().synthesize(make_request())
        kwargs = mock_post.call_args[1]
        assert kwargs["headers"]["X-Goog-Api-Key"] == "fake-api-key"
        # Must NOT be in query params
        assert "params" not in kwargs or kwargs.get("params") is None

    def test_request_body_structure_in_text_mode(self):
        """Payload must use 'text' key when InputMode.TEXT."""
        with patch("requests.post", return_value=_ok_response()) as mock_post:
            GoogleTTSAdapter().synthesize(make_request(text="Test text"))
        payload = mock_post.call_args[1]["json"]
        assert "text" in payload["input"]
        assert payload["input"]["text"] == "Test text"
        assert "ssml" not in payload["input"]

    def test_request_body_uses_ssml_key_in_ssml_mode(self):
        """Payload must use 'ssml' key when InputMode.SSML."""
        ssml = "<speak>Hello <break time='500ms'/></speak>"
        with patch("requests.post", return_value=_ok_response()) as mock_post:
            GoogleTTSAdapter().synthesize(
                make_request(text=ssml, input_mode=InputMode.SSML)
            )
        payload = mock_post.call_args[1]["json"]
        assert "ssml" in payload["input"]
        assert payload["input"]["ssml"] == ssml
        assert "text" not in payload["input"]

    def test_voice_fields_in_payload(self):
        with patch("requests.post", return_value=_ok_response()) as mock_post:
            GoogleTTSAdapter().synthesize(make_request())
        payload = mock_post.call_args[1]["json"]
        assert payload["voice"]["languageCode"] == "en-US"
        assert payload["voice"]["name"] == "en-US-Neural2-C"
        assert payload["voice"]["ssmlGender"] == "NEUTRAL"

    def test_audio_config_fields_in_payload(self):
        with patch("requests.post", return_value=_ok_response()) as mock_post:
            GoogleTTSAdapter().synthesize(make_request())
        payload = mock_post.call_args[1]["json"]
        assert payload["audioConfig"]["audioEncoding"] == "MP3"
        assert payload["audioConfig"]["speakingRate"] == 1.0
        assert payload["audioConfig"]["pitch"] == 0.0
        assert payload["audioConfig"]["volumeGainDb"] == 0.0

    def test_effects_profile_included_when_set(self):
        with patch("requests.post", return_value=_ok_response()) as mock_post:
            GoogleTTSAdapter().synthesize(
                make_request(effects_profile_id="headphone-class-device")
            )
        payload = mock_post.call_args[1]["json"]
        assert "effectsProfileId" in payload["audioConfig"]
        assert payload["audioConfig"]["effectsProfileId"] == ["headphone-class-device"]

    def test_effects_profile_excluded_when_none(self):
        with patch("requests.post", return_value=_ok_response()) as mock_post:
            GoogleTTSAdapter().synthesize(make_request(effects_profile_id=None))
        payload = mock_post.call_args[1]["json"]
        assert "effectsProfileId" not in payload["audioConfig"]

    def test_api_error_400_raises_value_error(self):
        with patch("requests.post", return_value=_err_response(400, "API key not valid.")):
            with pytest.raises(ValueError) as exc_info:
                GoogleTTSAdapter().synthesize(make_request())
        assert "400" in str(exc_info.value)
        assert "API key not valid" in str(exc_info.value)

    def test_api_error_403_raises_value_error(self):
        with patch("requests.post", return_value=_err_response(403, "Forbidden: billing not enabled.")):
            with pytest.raises(ValueError) as exc_info:
                GoogleTTSAdapter().synthesize(make_request())
        assert "403" in str(exc_info.value)

    def test_api_error_500_raises_value_error(self):
        with patch("requests.post", return_value=_err_response(500, "Internal Server Error")):
            with pytest.raises(ValueError):
                GoogleTTSAdapter().synthesize(make_request())

    def test_character_count_matches_text_length(self):
        text = "This is exactly forty characters!!!!!"
        with patch("requests.post", return_value=_ok_response("xyz")):
            result = GoogleTTSAdapter().synthesize(make_request(text=text))
        assert result.character_count == len(text)

    def test_encoding_in_result_matches_settings(self):
        with patch("requests.post", return_value=_ok_response()):
            result = GoogleTTSAdapter().synthesize(make_request(encoding="OGG_OPUS"))
        assert result.encoding == "OGG_OPUS"

    def test_malformed_error_response_still_raises(self):
        """If JSON parsing the error body fails, still raises ValueError."""
        mock = MagicMock()
        mock.status_code = 503
        mock.json.side_effect = Exception("not json")
        mock.text = "Service Unavailable"
        with patch("requests.post", return_value=mock):
            with pytest.raises(ValueError) as exc_info:
                GoogleTTSAdapter().synthesize(make_request())
        assert "503" in str(exc_info.value)


# ══════════════════════════════════════════════
# list_voices()
# ══════════════════════════════════════════════

_SAMPLE_VOICES_RESPONSE = {
    "voices": [
        {
            "name": "en-US-Neural2-C",
            "languageCodes": ["en-US"],
            "ssmlGender": "FEMALE",
            "naturalSampleRateHertz": 24000,
        },
        {
            "name": "en-US-Neural2-D",
            "languageCodes": ["en-US"],
            "ssmlGender": "MALE",
            "naturalSampleRateHertz": 24000,
        },
        {
            "name": "fr-FR-Neural2-A",
            "languageCodes": ["fr-FR"],
            "ssmlGender": "FEMALE",
            "naturalSampleRateHertz": 24000,
        },
    ]
}


def _ok_voices_response(voices_data=None):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = voices_data or _SAMPLE_VOICES_RESPONSE
    return mock


class TestListVoices:
    def test_successful_list_voices_returns_list(self):
        with patch("requests.get", return_value=_ok_voices_response()):
            voices = GoogleTTSAdapter().list_voices(api_key="fake-key")
        assert isinstance(voices, list)
        assert len(voices) == 3

    def test_api_key_sent_as_header(self):
        with patch("requests.get", return_value=_ok_voices_response()) as mock_get:
            GoogleTTSAdapter().list_voices(api_key="fake-key")
        kwargs = mock_get.call_args[1]
        assert kwargs["headers"]["X-Goog-Api-Key"] == "fake-key"

    def test_no_language_code_sends_no_params(self):
        """When no language_code is given, params should be None (no query string)."""
        with patch("requests.get", return_value=_ok_voices_response()) as mock_get:
            GoogleTTSAdapter().list_voices(api_key="fake-key")
        kwargs = mock_get.call_args[1]
        assert kwargs.get("params") is None

    def test_with_language_code_sets_param(self):
        with patch("requests.get", return_value=_ok_voices_response()) as mock_get:
            GoogleTTSAdapter().list_voices(api_key="fake-key", language_code="en-US")
        kwargs = mock_get.call_args[1]
        assert kwargs["params"]["languageCode"] == "en-US"

    def test_translates_camel_case_to_snake_case(self):
        """API response fields (camelCase) must be normalised to snake_case."""
        with patch("requests.get", return_value=_ok_voices_response()):
            voices = GoogleTTSAdapter().list_voices(api_key="fake-key")
        v = voices[0]
        assert "name" in v
        assert "language_codes" in v          # camelCase: languageCodes
        assert "ssml_gender" in v             # camelCase: ssmlGender
        assert "natural_sample_rate_hertz" in v  # camelCase: naturalSampleRateHertz
        # Ensure no raw camelCase keys leaked through
        assert "languageCodes" not in v
        assert "ssmlGender" not in v
        assert "naturalSampleRateHertz" not in v

    def test_voice_fields_have_correct_values(self):
        with patch("requests.get", return_value=_ok_voices_response()):
            voices = GoogleTTSAdapter().list_voices(api_key="fake-key")
        v = voices[0]
        assert v["name"] == "en-US-Neural2-C"
        assert v["language_codes"] == ["en-US"]
        assert v["ssml_gender"] == "FEMALE"
        assert v["natural_sample_rate_hertz"] == 24000

    def test_returns_empty_list_when_no_voices(self):
        with patch("requests.get", return_value=_ok_voices_response({"voices": []})):
            voices = GoogleTTSAdapter().list_voices(api_key="fake-key")
        assert voices == []

    def test_error_response_raises_value_error(self):
        mock = MagicMock()
        mock.status_code = 401
        mock.json.return_value = {"error": {"message": "Request is missing required authentication credential."}}
        mock.text = "Unauthorized"
        with patch("requests.get", return_value=mock):
            with pytest.raises(ValueError) as exc_info:
                GoogleTTSAdapter().list_voices(api_key="bad-key")
        assert "401" in str(exc_info.value)
        assert "authentication" in str(exc_info.value).lower()

    def test_error_message_contains_http_status(self):
        mock = MagicMock()
        mock.status_code = 429
        mock.json.return_value = {"error": {"message": "Quota exceeded."}}
        mock.text = "Too Many Requests"
        with patch("requests.get", return_value=mock):
            with pytest.raises(ValueError) as exc_info:
                GoogleTTSAdapter().list_voices(api_key="k")
        assert "429" in str(exc_info.value)

    def test_calls_correct_voices_endpoint(self):
        with patch("requests.get", return_value=_ok_voices_response()) as mock_get:
            GoogleTTSAdapter().list_voices(api_key="k")
        url = mock_get.call_args[0][0]
        assert "texttospeech.googleapis.com" in url
        assert "voices" in url


# ══════════════════════════════════════════════
# Retry behaviour
# ══════════════════════════════════════════════

def _retryable_response(status: int, message: str = "Transient error") -> MagicMock:
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = {"error": {"message": message}}
    mock.text = message
    return mock


class TestSynthesizeRetry:
    """Verify that synthesize() retries on transient HTTP errors and raises
    ValueError after exhausting all attempts."""

    def test_retries_on_429_and_eventually_raises(self):
        """Three consecutive 429 responses should exhaust retries and raise ValueError."""
        retryable = _retryable_response(429, "Quota exceeded.")
        with patch("requests.post", return_value=retryable) as mock_post:
            with pytest.raises(ValueError, match="429"):
                GoogleTTSAdapter().synthesize(make_request())
        # tenacity allows up to 3 attempts
        assert mock_post.call_count == 3

    def test_retries_on_503_and_eventually_raises(self):
        """Three consecutive 503 responses should exhaust retries and raise ValueError."""
        retryable = _retryable_response(503, "Service Unavailable")
        with patch("requests.post", return_value=retryable) as mock_post:
            with pytest.raises(ValueError, match="503"):
                GoogleTTSAdapter().synthesize(make_request())
        assert mock_post.call_count == 3

    def test_succeeds_after_one_retry(self):
        """First call returns 429, second call succeeds — result must be returned."""
        retryable = _retryable_response(429, "Quota exceeded.")
        ok = _ok_response("dGVzdA==")
        with patch("requests.post", side_effect=[retryable, ok]) as mock_post:
            result = GoogleTTSAdapter().synthesize(make_request())
        assert result.audio_content_b64 == "dGVzdA=="
        assert mock_post.call_count == 2

    def test_non_retryable_400_does_not_retry(self):
        """HTTP 400 is not in the retryable set — should fail immediately."""
        bad = _err_response(400, "API key not valid.")
        with patch("requests.post", return_value=bad) as mock_post:
            with pytest.raises(ValueError, match="400"):
                GoogleTTSAdapter().synthesize(make_request())
        assert mock_post.call_count == 1

    def test_non_retryable_403_does_not_retry(self):
        bad = _err_response(403, "Forbidden.")
        with patch("requests.post", return_value=bad) as mock_post:
            with pytest.raises(ValueError, match="403"):
                GoogleTTSAdapter().synthesize(make_request())
        assert mock_post.call_count == 1

    def test_timeout_triggers_retry(self):
        """requests.Timeout is a retryable exception — should retry up to 3 times."""
        import requests as req
        with patch("requests.post", side_effect=req.Timeout("timed out")) as mock_post:
            with pytest.raises(req.Timeout):
                GoogleTTSAdapter().synthesize(make_request())
        assert mock_post.call_count == 3


class TestListVoicesRetry:
    """Verify that list_voices() retries on transient HTTP errors."""

    def test_retries_on_429_and_eventually_raises(self):
        retryable = _retryable_response(429, "Quota exceeded.")
        with patch("requests.get", return_value=retryable) as mock_get:
            with pytest.raises(ValueError, match="429"):
                GoogleTTSAdapter().list_voices(api_key="k")
        assert mock_get.call_count == 3

    def test_retries_on_503_and_eventually_raises(self):
        retryable = _retryable_response(503, "Service Unavailable")
        with patch("requests.get", return_value=retryable) as mock_get:
            with pytest.raises(ValueError, match="503"):
                GoogleTTSAdapter().list_voices(api_key="k")
        assert mock_get.call_count == 3

    def test_succeeds_after_one_retry(self):
        retryable = _retryable_response(429, "Quota exceeded.")
        ok = _ok_voices_response()
        with patch("requests.get", side_effect=[retryable, ok]) as mock_get:
            voices = GoogleTTSAdapter().list_voices(api_key="k")
        assert len(voices) == 3
        assert mock_get.call_count == 2

    def test_non_retryable_401_does_not_retry(self):
        bad = MagicMock()
        bad.status_code = 401
        bad.json.return_value = {"error": {"message": "Unauthorized"}}
        bad.text = "Unauthorized"
        with patch("requests.get", return_value=bad) as mock_get:
            with pytest.raises(ValueError, match="401"):
                GoogleTTSAdapter().list_voices(api_key="k")
        assert mock_get.call_count == 1
