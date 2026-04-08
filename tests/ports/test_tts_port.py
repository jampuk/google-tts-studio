"""
Tests verifying that ITTSPort is a well-formed abstract base class and that
GoogleTTSAdapter correctly implements it.
"""
import pytest
from abc import ABC

from src.ports.tts_port import ITTSPort
from src.adapters.google_tts_adapter import GoogleTTSAdapter
from src.domain.models import TTSRequest, TTSSettings, TTSResult


class TestITTSPortDefinition:
    def test_port_is_abstract(self):
        assert issubclass(ITTSPort, ABC)

    def test_port_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            ITTSPort()  # type: ignore[abstract]

    def test_port_has_synthesize_method(self):
        assert hasattr(ITTSPort, "synthesize")
        assert callable(ITTSPort.synthesize)

    def test_port_has_list_voices_method(self):
        assert hasattr(ITTSPort, "list_voices")
        assert callable(ITTSPort.list_voices)


class TestGoogleTTSAdapterCompliance:
    def test_adapter_is_instance_of_port(self):
        adapter = GoogleTTSAdapter()
        assert isinstance(adapter, ITTSPort)

    def test_adapter_implements_synthesize(self):
        assert hasattr(GoogleTTSAdapter, "synthesize")
        assert callable(GoogleTTSAdapter.synthesize)

    def test_adapter_implements_list_voices(self):
        assert hasattr(GoogleTTSAdapter, "list_voices")
        assert callable(GoogleTTSAdapter.list_voices)

    def test_adapter_can_be_assigned_to_port_typed_variable(self):
        """Verify the assignment pattern used in app.py works at runtime."""
        adapter: ITTSPort = GoogleTTSAdapter()
        assert isinstance(adapter, ITTSPort)


class TestConcretePortImplementation:
    """A minimal in-process stub verifies the ABC contract is enforceable."""

    def test_subclass_without_synthesize_cannot_be_instantiated(self):
        class BrokenAdapter(ITTSPort):
            def list_voices(self, api_key, language_code=None):
                return []
            # synthesize intentionally omitted

        with pytest.raises(TypeError):
            BrokenAdapter()

    def test_subclass_without_list_voices_cannot_be_instantiated(self):
        class BrokenAdapter(ITTSPort):
            def synthesize(self, request):
                return None
            # list_voices intentionally omitted

        with pytest.raises(TypeError):
            BrokenAdapter()

    def test_complete_subclass_can_be_instantiated(self):
        class StubAdapter(ITTSPort):
            def synthesize(self, request: TTSRequest) -> TTSResult:
                return TTSResult(audio_content_b64="abc", encoding="MP3", character_count=0)

            def list_voices(self, api_key: str, language_code=None) -> list:
                return []

        adapter = StubAdapter()
        assert isinstance(adapter, ITTSPort)

    def test_stub_synthesize_is_callable(self):
        class StubAdapter(ITTSPort):
            def synthesize(self, request: TTSRequest) -> TTSResult:
                return TTSResult(audio_content_b64="xyz", encoding="MP3", character_count=5)

            def list_voices(self, api_key: str, language_code=None) -> list:
                return []

        adapter = StubAdapter()
        settings = TTSSettings()
        request = TTSRequest(text="Hello", settings=settings, api_key="key")
        result = adapter.synthesize(request)
        assert isinstance(result, TTSResult)
        assert result.encoding == "MP3"

    def test_stub_list_voices_is_callable(self):
        class StubAdapter(ITTSPort):
            def synthesize(self, request: TTSRequest) -> TTSResult:
                return TTSResult(audio_content_b64="", encoding="MP3", character_count=0)

            def list_voices(self, api_key: str, language_code=None) -> list:
                return [{"name": "en-US-Neural2-C"}]

        adapter = StubAdapter()
        voices = adapter.list_voices(api_key="key")
        assert isinstance(voices, list)
        assert len(voices) == 1
