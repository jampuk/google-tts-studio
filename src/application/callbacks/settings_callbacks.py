"""Callbacks related to settings persistence, dark mode, API key, and control state."""
import logging

import dash
from dash import Input, Output, State, ctx
from dash.exceptions import PreventUpdate

from src.application.app import app
from src.application.callbacks.helpers import ADVANCED_DEFAULTS, GLOW_STYLE, NO_GLOW_STYLE
from src.domain.models import InputMode

logger = logging.getLogger(__name__)


# ── Dark mode ──────────────────────────────────────────────────────────────────

@app.callback(
    Output("mantine-provider", "forceColorScheme"),
    Output("dark-mode-toggle", "children"),
    Input("color-scheme-store", "data"),
    prevent_initial_call=False,
)
def apply_color_scheme(scheme):
    scheme = scheme or "light"
    icon = "☀" if scheme == "dark" else "🌙"
    return scheme, icon


@app.callback(
    Output("color-scheme-store", "data"),
    Input("dark-mode-toggle", "n_clicks"),
    State("color-scheme-store", "data"),
    prevent_initial_call=True,
)
def toggle_dark_mode(n_clicks, current_scheme):
    if not n_clicks:
        raise PreventUpdate
    return "dark" if (current_scheme or "light") == "light" else "light"


# ── Controls enable/disable + accordion ───────────────────────────────────────

@app.callback(
    Output("title-input", "disabled"),
    Output("text-input", "disabled"),
    Output("language-select", "disabled"),
    Output("speaking-rate-slider", "disabled"),
    Output("pitch-slider", "disabled"),
    Output("volume-gain-slider", "disabled"),
    Output("effects-profile-select", "disabled"),
    Output("refresh-voices-btn", "disabled"),
    Output("download-btn", "disabled"),
    Output("api-key-accordion", "value"),
    Output("reset-all-advanced-btn", "disabled"),
    Output("reset-speaking-rate-btn", "disabled"),
    Output("reset-pitch-btn", "disabled"),
    Output("reset-volume-gain-btn", "disabled"),
    Output("reset-effects-profile-btn", "disabled"),
    Output("input-mode-toggle", "disabled"),
    Input("api-key-store", "data"),
    prevent_initial_call=False,
)
def toggle_controls_on_api_key(api_key_data):
    has_key = bool(api_key_data and str(api_key_data).strip())
    disabled = not has_key
    accordion_value = None if has_key else "api-key"
    # gender-select, voice-select, encoding-select, generate-btn, and
    # preview-voice-btn are controlled by the progressive_voice_settings callback
    return (disabled,) * 9 + (accordion_value,) + (disabled,) * 6


# ── Load saved settings on startup ────────────────────────────────────────────

@app.callback(
    Output("language-select", "value"),
    Output("voice-select", "value"),
    Output("gender-select", "value"),
    Output("encoding-select", "value"),
    Output("speaking-rate-slider", "value"),
    Output("pitch-slider", "value"),
    Output("volume-gain-slider", "value"),
    Output("effects-profile-select", "value"),
    Output("input-mode-toggle", "value"),
    Input("settings-store", "data"),
    prevent_initial_call=False,
)
def load_settings_on_startup(settings_data):
    s = settings_data or {}
    return (
        s.get("language_code") or None,
        s.get("voice_name") or None,
        s.get("ssml_gender") or None,
        s.get("audio_encoding") or None,
        s.get("speaking_rate", ADVANCED_DEFAULTS["speaking_rate"]),
        s.get("pitch", ADVANCED_DEFAULTS["pitch"]),
        s.get("volume_gain_db", ADVANCED_DEFAULTS["volume_gain_db"]),
        s.get("effects_profile_id", ADVANCED_DEFAULTS["effects_profile_id"]),
        s.get("input_mode", InputMode.TEXT),
    )


@app.callback(
    Output("api-key-input", "value"),
    Input("api-key-store", "data"),
    prevent_initial_call=False,
)
def load_api_key_on_startup(api_key_data):
    return api_key_data or ""


# ── Progressive voice settings disclosure ─────────────────────────────────────

@app.callback(
    Output("gender-select", "disabled"),
    Output("voice-select", "disabled"),
    Output("encoding-select", "disabled"),
    Output("generate-btn", "disabled"),
    Output("preview-voice-btn", "disabled"),
    Output("gender-select-wrapper", "style"),
    Output("voice-select-wrapper", "style"),
    Output("encoding-select-wrapper", "style"),
    Input("language-select", "value"),
    Input("gender-select", "value"),
    Input("voice-select", "value"),
    Input("encoding-select", "value"),
    Input("text-input", "value"),
    Input("api-key-store", "data"),
    prevent_initial_call=False,
)
def progressive_voice_settings(language, gender, voice, encoding, text, api_key_data):
    has_key = bool(api_key_data and str(api_key_data).strip())

    if not has_key:
        return True, True, True, True, True, NO_GLOW_STYLE, NO_GLOW_STYLE, NO_GLOW_STYLE

    has_language = bool(language)
    has_gender = bool(gender)
    has_voice = bool(voice)
    has_encoding = bool(encoding)
    has_text = bool((text or "").strip())

    gender_disabled = not has_language
    voice_disabled = not (has_language and has_gender)
    encoding_disabled = not (has_language and has_gender and has_voice)
    generate_disabled = not (has_language and has_gender and has_voice and has_encoding and has_text)
    preview_disabled = not (has_language and has_gender and has_voice)

    gender_style = GLOW_STYLE if (has_language and not has_gender) else NO_GLOW_STYLE
    voice_style = GLOW_STYLE if (has_gender and not has_voice) else NO_GLOW_STYLE
    encoding_style = GLOW_STYLE if (has_voice and not has_encoding) else NO_GLOW_STYLE

    return (
        gender_disabled,
        voice_disabled,
        encoding_disabled,
        generate_disabled,
        preview_disabled,
        gender_style,
        voice_style,
        encoding_style,
    )


# ── Reset advanced settings ───────────────────────────────────────────────────

@app.callback(
    Output("speaking-rate-slider", "value", allow_duplicate=True),
    Output("pitch-slider", "value", allow_duplicate=True),
    Output("volume-gain-slider", "value", allow_duplicate=True),
    Output("effects-profile-select", "value", allow_duplicate=True),
    Input("reset-all-advanced-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_all_advanced(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return (
        ADVANCED_DEFAULTS["speaking_rate"],
        ADVANCED_DEFAULTS["pitch"],
        ADVANCED_DEFAULTS["volume_gain_db"],
        ADVANCED_DEFAULTS["effects_profile_id"],
    )


@app.callback(
    Output("speaking-rate-slider", "value", allow_duplicate=True),
    Input("reset-speaking-rate-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_speaking_rate(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return ADVANCED_DEFAULTS["speaking_rate"]


@app.callback(
    Output("pitch-slider", "value", allow_duplicate=True),
    Input("reset-pitch-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_pitch(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return ADVANCED_DEFAULTS["pitch"]


@app.callback(
    Output("volume-gain-slider", "value", allow_duplicate=True),
    Input("reset-volume-gain-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_volume_gain(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return ADVANCED_DEFAULTS["volume_gain_db"]


@app.callback(
    Output("effects-profile-select", "value", allow_duplicate=True),
    Input("reset-effects-profile-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_effects_profile(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return ADVANCED_DEFAULTS["effects_profile_id"]


# ── Save settings on change ───────────────────────────────────────────────────

@app.callback(
    Output("settings-store", "data"),
    Input("language-select", "value"),
    Input("voice-select", "value"),
    Input("gender-select", "value"),
    Input("encoding-select", "value"),
    Input("speaking-rate-slider", "value"),
    Input("pitch-slider", "value"),
    Input("volume-gain-slider", "value"),
    Input("effects-profile-select", "value"),
    Input("input-mode-toggle", "value"),
    prevent_initial_call=True,
)
def save_settings(language_code, voice_name, ssml_gender, audio_encoding,
                  speaking_rate, pitch, volume_gain_db, effects_profile_id,
                  input_mode):
    return {
        "language_code": language_code or None,
        "voice_name": voice_name or None,
        "ssml_gender": ssml_gender or None,
        "audio_encoding": audio_encoding or None,
        "speaking_rate": speaking_rate if speaking_rate is not None else ADVANCED_DEFAULTS["speaking_rate"],
        "pitch": pitch if pitch is not None else ADVANCED_DEFAULTS["pitch"],
        "volume_gain_db": volume_gain_db if volume_gain_db is not None else ADVANCED_DEFAULTS["volume_gain_db"],
        "effects_profile_id": effects_profile_id,
        "input_mode": input_mode or InputMode.TEXT,
    }


# ── Save API key ──────────────────────────────────────────────────────────────

@app.callback(
    Output("api-key-store", "data"),
    Output("api-key-status", "children"),
    Output("api-key-status", "c"),
    Input("save-api-key-btn", "n_clicks"),
    State("api-key-input", "value"),
    prevent_initial_call=True,
)
def save_api_key(n_clicks, api_key_value):
    if not n_clicks:
        raise PreventUpdate
    key = (api_key_value or "").strip()
    if not key:
        return dash.no_update, "⚠ Please enter a valid API key.", "red"
    return key, "✓ API key saved to browser storage.", "green"


# ── SSML hint visibility ──────────────────────────────────────────────────────

@app.callback(
    Output("ssml-hint-wrapper", "style"),
    Output("text-input", "placeholder"),
    Input("input-mode-toggle", "value"),
    prevent_initial_call=False,
)
def update_input_mode_ui(mode):
    if mode == InputMode.SSML:
        return (
            {"display": "block"},
            (
                "<speak>\n"
                "  Hello! Use <break time=\"500ms\"/> SSML tags here.\n"
                "  <prosody rate=\"slow\">Speak slowly.</prosody>\n"
                "</speak>"
            ),
        )
    return (
        {"display": "none"},
        "Enter text to convert to speech...",
    )


# ── Clear Data modal ──────────────────────────────────────────────────────────

@app.callback(
    Output("clear-data-modal", "opened"),
    Input("clear-data-btn", "n_clicks"),
    Input("clear-data-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_clear_data_modal(open_clicks, cancel_clicks):
    if ctx.triggered_id == "clear-data-btn":
        return True
    return False


@app.callback(
    Output("settings-store", "data", allow_duplicate=True),
    Output("history-store", "data", allow_duplicate=True),
    Output("api-key-store", "data", allow_duplicate=True),
    Output("voices-store", "data", allow_duplicate=True),
    Output("api-key-input", "value", allow_duplicate=True),
    Output("clear-data-modal", "opened", allow_duplicate=True),
    Output("api-key-status", "children", allow_duplicate=True),
    Output("api-key-status", "c", allow_duplicate=True),
    Input("clear-data-confirm-btn", "n_clicks"),
    prevent_initial_call=True,
)
def confirm_clear_data(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return {}, [], None, [], "", False, "✓ All app data cleared.", "dimmed"
