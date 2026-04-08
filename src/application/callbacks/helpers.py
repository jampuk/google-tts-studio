"""Shared helpers, constants, and style definitions used across callbacks.

ADVANCED_DEFAULTS is derived directly from TTSSettings field defaults to
eliminate the DRY violation of hardcoding the same values in two places.
"""
import dataclasses

from src.domain.models import AudioEncoding, TTSSettings

# ── Gender display symbols ────────────────────────────────────────────────────

GENDER_SYMBOL: dict[str, str] = {
    "MALE": "♂",
    "FEMALE": "♀",
    "NEUTRAL": "⚥",
    "SSML_VOICE_GENDER_UNSPECIFIED": "?",
}

# ── Advanced settings defaults ────────────────────────────────────────────────
# Derived from TTSSettings field defaults — single source of truth.
# If a default ever changes in TTSSettings, this dict updates automatically.

_settings_field_defaults = {
    f.name: f.default
    for f in dataclasses.fields(TTSSettings)
    if f.default is not dataclasses.MISSING
}

ADVANCED_DEFAULTS: dict[str, object] = {
    k: _settings_field_defaults[k]
    for k in ("speaking_rate", "pitch", "volume_gain_db", "effects_profile_id")
}

# ── Progressive disclosure glow styles ───────────────────────────────────────

GLOW_STYLE: dict[str, str] = {
    "boxShadow": "0 0 0 3px rgba(124, 58, 237, 0.35)",
    "borderRadius": "8px",
    "transition": "box-shadow 0.3s",
}
NO_GLOW_STYLE: dict[str, str] = {
    "boxShadow": "none",
    "borderRadius": "8px",
    "transition": "box-shadow 0.3s",
}

# ── Error helper for generate_speech callback ─────────────────────────────────

import dash  # noqa: E402 — import after constants to keep file readable


def err(notification: object) -> tuple:
    """Return an 8-element no-op tuple for the generate_speech callback error path."""
    return (
        dash.no_update,  # current-audio-store
        dash.no_update,  # history-store
        dash.no_update,  # audio-player src
        dash.no_update,  # audio-player-card style
        notification,    # notification-area
        dash.no_update,  # text-input value
        False,           # generate-btn loading
        False,           # generate-btn disabled
    )


# ── Voice option builders ─────────────────────────────────────────────────────

def build_language_options(voices: list[dict]) -> list[dict]:
    """Return sorted unique language options from a voice list."""
    seen: dict[str, str] = {}
    for v in voices:
        for lang in v.get("language_codes", []):
            if lang not in seen:
                seen[lang] = lang
    return sorted([{"value": k, "label": k} for k in seen], key=lambda x: x["value"])


def build_gender_options(voices: list[dict], language_code: str) -> list[dict]:
    """Return gender options available for *language_code*, always including 'ALL'."""
    genders: set[str] = set()
    for v in voices:
        if language_code in v.get("language_codes", []):
            genders.add(v.get("ssml_gender", "NEUTRAL"))
    options = [{"value": "ALL", "label": "All Genders"}]
    for g in sorted(genders):
        symbol = GENDER_SYMBOL.get(g, "")
        options.append({"value": g, "label": f"{g} {symbol}"})
    return options


def build_voice_options(
    voices: list[dict],
    language_code: str,
    gender: str | None = None,
) -> list[dict]:
    """Return voice options filtered by *language_code* and optionally *gender*."""
    options = []
    for v in voices:
        if language_code not in v.get("language_codes", []):
            continue
        v_gender = v.get("ssml_gender", "NEUTRAL")
        if gender and gender != "ALL" and v_gender != gender:
            continue
        symbol = GENDER_SYMBOL.get(v_gender, "")
        rate = v.get("natural_sample_rate_hertz", 0)
        label = f"{v['name']}  {symbol}  {rate}Hz"
        options.append({"value": v["name"], "label": label})
    return sorted(options, key=lambda x: x["value"])
