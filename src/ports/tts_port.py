from abc import ABC, abstractmethod
from typing import Optional

from src.domain.models import TTSRequest, TTSResult


class ITTSPort(ABC):
    @abstractmethod
    def synthesize(self, request: TTSRequest) -> TTSResult:
        ...

    @abstractmethod
    def list_voices(self, api_key: str, language_code: Optional[str] = None) -> list:
        """Return a list of voice dicts from the Google TTS API.

        Each dict has keys: name, languageCodes, ssmlGender, naturalSampleRateHertz.
        Raises ValueError on API errors.
        """
        ...
