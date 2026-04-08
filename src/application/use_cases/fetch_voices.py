import logging
from src.ports.tts_port import ITTSPort

logger = logging.getLogger(__name__)


class FetchVoicesUseCase:
    """Fetches the available TTS voices from the underlying provider.

    Encapsulates key validation and adapter invocation so that the callback
    layer stays free of API-interaction details.
    """

    def __init__(self, tts_port: ITTSPort) -> None:
        self._port = tts_port

    def execute(self, api_key: str) -> list[dict]:
        """Return the list of available voice dicts.

        Args:
            api_key: A non-empty Google Cloud API key string.

        Returns:
            A list of snake_case voice dicts as returned by the adapter.

        Raises:
            ValueError: If the API key is empty or the adapter call fails.
        """
        key = (api_key or "").strip()
        if not key:
            raise ValueError("API key must not be empty.")

        logger.info("FetchVoicesUseCase: fetching all voices")
        voices = self._port.list_voices(api_key=key)
        logger.info("FetchVoicesUseCase: fetched %d voices", len(voices))
        return voices
