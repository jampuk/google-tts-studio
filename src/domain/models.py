import html
import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


def sanitize_text(raw: str) -> str:
    """Strip HTML tags, decode HTML entities, remove Markdown syntax, and
    normalise whitespace so the resulting string is clean plain text suitable
    for Google TTS.

    Steps applied in order:
    1. Strip fenced code blocks (``` … ```) — replace with a single space
    2. Strip inline code (`…`)
    3. Strip ATX headings (# … ######)
    4. Strip setext underlines (=== or ---)
    5. Strip horizontal rules (--- / *** / ___)
    6. Strip blockquotes (>)
    7. Strip unordered list markers (-, *, +)
    8. Strip ordered list markers (1. 2. etc.)
    9. Strip bold/italic (**…** / __…__ / *…* / _…_)
    10. Strip Markdown links [text](url) → keep text
    11. Strip Markdown images ![alt](url) → keep alt
    12. Strip bare URLs (http/https)
    13. Strip HTML tags (< … >)
    14. Decode HTML entities (&amp; → &)
    15. Collapse multiple blank lines to a single line break
    16. Collapse multiple spaces/tabs to a single space
    17. Strip leading/trailing whitespace
    """
    text = raw

    # 1. Fenced code blocks
    text = re.sub(r"```[\s\S]*?```", " ", text)
    # 2. Inline code
    text = re.sub(r"`[^`]*`", " ", text)
    # 3. ATX headings
    text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 4. Setext underlines
    text = re.sub(r"^\s*[=\-]{2,}\s*$", "", text, flags=re.MULTILINE)
    # 5. Horizontal rules
    text = re.sub(r"^\s*([*\-_])\s*\1\s*\1[\s*\-_]*$", "", text, flags=re.MULTILINE)
    # 6. Blockquotes
    text = re.sub(r"^\s*>+\s?", "", text, flags=re.MULTILINE)
    # 7. Unordered list markers
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    # 8. Ordered list markers
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # 9. Bold/italic (order matters: longest pattern first)
    text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)
    text = re.sub(r"_{3}(.+?)_{3}", r"\1", text)
    text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text)
    text = re.sub(r"_{2}(.+?)_{2}", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # 10. Markdown links
    text = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r"\1", text)   # images first
    text = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r"\1", text)    # then links
    # 11. Bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # 12. HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # 13. HTML entities
    text = html.unescape(text)
    # 14. Collapse blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 15. Collapse whitespace within lines
    text = re.sub(r"[ \t]+", " ", text)
    # 16. Strip leading/trailing whitespace per line and overall
    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()


def validate_ssml(ssml: str) -> None:
    """Validate that *ssml* is well-formed XML with a <speak> root element.

    Raises ValueError with a descriptive message if validation fails, allowing
    the application layer to surface the error to the user before making an API
    call.
    """
    import xml.etree.ElementTree as ET
    stripped = ssml.strip()
    if not stripped:
        raise ValueError("SSML content is empty.")
    try:
        root = ET.fromstring(stripped)
    except ET.ParseError as exc:
        raise ValueError(f"SSML is not valid XML: {exc}") from exc
    # Strip any namespace — Google TTS accepts both bare and namespaced <speak>
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if tag != "speak":
        raise ValueError(
            f"SSML root element must be <speak>, got <{tag}>."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Language-aware preview phrases
# Used by PreviewVoiceUseCase to audition voices in a meaningful language.
# Keys are BCP-47 language *prefixes* (before the '-').
# ──────────────────────────────────────────────────────────────────────────────
PREVIEW_PHRASES: dict[str, str] = {
    "en": "The quick brown fox jumps over the lazy dog.",
    "fr": "Le renard brun rapide saute par-dessus le chien paresseux.",
    "de": "Der schnelle braune Fuchs springt über den faulen Hund.",
    "es": "El rápido zorro marrón salta sobre el perro perezoso.",
    "it": "La volpe marrone veloce salta sopra il cane pigro.",
    "pt": "A raposa marrom rápida pula sobre o cachorro preguiçoso.",
    "nl": "De snelle bruine vos springt over de luie hond.",
    "pl": "Szybki brązowy lis przeskakuje nad leniwym psem.",
    "ru": "Быстрая коричневая лиса прыгает через ленивую собаку.",
    "ja": "素早い茶色のキツネは怠け者の犬を飛び越えます。",
    "zh": "敏捷的棕色狐狸跳过了懒狗。",
    "ko": "빠른 갈색 여우가 게으른 개를 뛰어넘습니다.",
    "ar": "الثعلب البني السريع يقفز فوق الكلب الكسول.",
    "hi": "तेज़ भूरी लोमड़ी आलसी कुत्ते के ऊपर कूदती है।",
    "tr": "Hızlı kahverengi tilki tembel köpeğin üzerinden atlar.",
    "sv": "Den snabba bruna räven hoppar över den lata hunden.",
    "da": "Den hurtige brune ræv hopper over den dovne hund.",
    "fi": "Nopea ruskea kettu hyppää laiskan koiran yli.",
    "nb": "Den raske brune reven hopper over den late hunden.",
    "cs": "Rychlá hnědá liška přeskočí líného psa.",
    "sk": "Rýchla hnedá líška preskočí lenivého psa.",
    "uk": "Швидка руда лисиця стрибає через ледачого пса.",
    "id": "Rubah coklat yang cepat melompati anjing yang malas.",
    "ms": "Rubah perang yang pantas melompat ke atas anjing yang malas.",
    "th": "สุนัขจิ้งจอกสีน้ำตาลที่รวดเร็วกระโดดข้ามสุนัขขี้เกียจ",
    "vi": "Con cáo nâu nhanh nhẹn nhảy qua con chó lười biếng.",
    "el": "Η γρήγορη καφέ αλεπού πηδά πάνω από τον τεμπέλη σκύλο.",
    "ro": "Vulpea brună rapidă sare peste câinele leneș.",
    "hu": "A gyors barna róka átugorja a lusta kutyát.",
}


def get_preview_phrase(language_code: str) -> str:
    """Return an appropriate preview phrase for *language_code*.

    Matches on the language prefix (e.g. "en" from "en-US").
    Falls back to English if the language is not in PREVIEW_PHRASES.
    """
    prefix = language_code.split("-")[0].lower() if language_code else "en"
    return PREVIEW_PHRASES.get(prefix, PREVIEW_PHRASES["en"])


class AudioEncoding(str, Enum):
    """Audio encoding formats supported by the Google TTS API.

    Each member carries its MIME type and file extension as attributes,
    eliminating the need for parallel ENCODING_MIME / ENCODING_EXT dicts
    in the application layer.
    """

    def __new__(cls, value: str, mime: str, ext: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.mime = mime          # type: ignore[attr-defined]
        obj.ext = ext            # type: ignore[attr-defined]
        return obj

    MP3      = ("MP3",      "audio/mpeg",  ".mp3")
    LINEAR16 = ("LINEAR16", "audio/wav",   ".wav")
    OGG_OPUS = ("OGG_OPUS", "audio/ogg",   ".ogg")
    MULAW    = ("MULAW",    "audio/basic", ".au")
    ALAW     = ("ALAW",     "audio/pcm",   ".alaw")

    @classmethod
    def from_str(cls, value: str) -> "AudioEncoding":
        """Return the member for *value*, raising ``ValueError`` if not found."""
        try:
            return cls(value)
        except ValueError:
            valid = [m.value for m in cls]
            raise ValueError(
                f"Unknown audio encoding {value!r}. Valid values: {valid}"
            )


class InputMode(str, Enum):
    """Controls whether the TTS API receives plain text or SSML markup."""
    TEXT = "text"
    SSML = "ssml"


def utf8_byte_length(text: str) -> int:
    """Return the number of UTF-8 encoded bytes in *text*.

    The Google TTS API limit is 5 000 bytes (UTF-8), not characters.
    Multibyte scripts (CJK, Arabic, Hindi, etc.) consume 3-4 bytes each,
    so this is the correct metric to validate against.
    """
    return len(text.encode("utf-8"))


@dataclass
class TTSSettings:
    language_code: str = "en-US"
    voice_name: str = "en-US-Neural2-C"
    ssml_gender: str = "NEUTRAL"
    audio_encoding: AudioEncoding = AudioEncoding.MP3
    speaking_rate: float = 1.0        # 0.25 – 4.0
    pitch: float = 0.0                # -20.0 – 20.0
    volume_gain_db: float = 0.0       # -96.0 – 16.0
    effects_profile_id: Optional[str] = None  # e.g. "headphone-class-device"
    input_mode: InputMode = InputMode.TEXT   # text or ssml

    def __post_init__(self) -> None:
        """Validate field ranges at construction time.

        Raises ValueError for any field that falls outside the bounds
        documented in the Google TTS API reference.
        """
        if not self.language_code or not self.language_code.strip():
            raise ValueError("TTSSettings.language_code must be a non-empty string.")
        if not self.voice_name or not self.voice_name.strip():
            raise ValueError("TTSSettings.voice_name must be a non-empty string.")
        if not (0.25 <= self.speaking_rate <= 4.0):
            raise ValueError(
                f"TTSSettings.speaking_rate must be between 0.25 and 4.0, "
                f"got {self.speaking_rate}."
            )
        if not (-20.0 <= self.pitch <= 20.0):
            raise ValueError(
                f"TTSSettings.pitch must be between -20.0 and 20.0, "
                f"got {self.pitch}."
            )
        if not (-96.0 <= self.volume_gain_db <= 16.0):
            raise ValueError(
                f"TTSSettings.volume_gain_db must be between -96.0 and 16.0, "
                f"got {self.volume_gain_db}."
            )


@dataclass
class TTSRequest:
    text: str
    settings: TTSSettings
    api_key: str


@dataclass
class TTSResult:
    audio_content_b64: str   # base64-encoded binary
    encoding: str
    character_count: int


@dataclass
class HistoryEntry:
    id: str
    title: str               # user-supplied title or auto-generated timestamp slug
    text_snippet: str        # first 80 chars
    full_text: str
    timestamp: str           # ISO format
    # audio_content_b64 intentionally omitted — audio is NOT stored in history
    # to keep browser localStorage small (see README).
    encoding: str
    settings: dict           # serialized TTSSettings
