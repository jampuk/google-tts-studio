"""Callbacks related to voice fetching, filtering, and preview."""
import logging

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, ctx
from dash.exceptions import PreventUpdate

from src.application.app import app, fetch_voices_uc, preview_voice_uc
from src.application.callbacks.helpers import (
    build_gender_options,
    build_language_options,
    build_voice_options,
)
from src.domain.models import AudioEncoding

logger = logging.getLogger(__name__)


# ── Fetch voices from Google API ──────────────────────────────────────────────
# Triggered by: api-key-store change (after save), startup-interval, or Refresh btn

@app.callback(
    Output("voices-store", "data"),
    Output("voice-count-badge", "children"),
    Output("notification-area", "children", allow_duplicate=True),
    Input("api-key-store", "data"),
    Input("startup-interval", "n_intervals"),
    Input("refresh-voices-btn", "n_clicks"),
    State("voices-store", "data"),
    prevent_initial_call=True,
)
def fetch_voices(api_key, n_intervals, refresh_clicks, existing_voices):
    triggered = ctx.triggered_id
    if not triggered:
        raise PreventUpdate

    key = (api_key or "").strip()
    if not key:
        raise PreventUpdate

    # On startup with cached voices, just update badge — don't re-fetch
    if triggered == "startup-interval" and existing_voices:
        return dash.no_update, f"{len(existing_voices)} voices", dash.no_update

    try:
        voices = fetch_voices_uc.execute(api_key=key)
    except Exception as exc:
        notif = dmc.Notification(
            id="n-voices-err",
            title="Voice Fetch Failed",
            message=str(exc)[:300],
            color="red",
            action="show",
        )
        return dash.no_update, dash.no_update, notif

    return voices, f"{len(voices)} voices", dash.no_update


# ── Update language dropdown from voices ──────────────────────────────────────

@app.callback(
    Output("language-select", "data"),
    Input("voices-store", "data"),
    prevent_initial_call=True,
)
def update_language_options(voices):
    if not voices:
        raise PreventUpdate
    return build_language_options(voices)


# ── Update gender options per language ────────────────────────────────────────

@app.callback(
    Output("gender-select", "data"),
    Output("gender-select", "value", allow_duplicate=True),
    Input("language-select", "value"),
    Input("voices-store", "data"),
    State("gender-select", "value"),
    prevent_initial_call=True,
)
def update_gender_options(language_code, voices, current_gender):
    if not voices or not language_code:
        raise PreventUpdate
    options = build_gender_options(voices, language_code)
    valid = {o["value"] for o in options}
    new_gender = current_gender if (current_gender and current_gender in valid) else None
    return options, new_gender


# ── Filter voice list by language + gender ────────────────────────────────────

@app.callback(
    Output("voice-select", "data"),
    Output("voice-select", "value", allow_duplicate=True),
    Output("preview-player", "src", allow_duplicate=True),
    Output("preview-player-wrapper", "style", allow_duplicate=True),
    Output("preview-voice-btn-wrapper", "style", allow_duplicate=True),
    Input("language-select", "value"),
    Input("gender-select", "value"),
    Input("voices-store", "data"),
    State("voice-select", "value"),
    prevent_initial_call=True,
)
def filter_voices(language_code, gender, voices, current_voice):
    if not voices:
        raise PreventUpdate
    if not language_code:
        raise PreventUpdate

    options = build_voice_options(voices, language_code, gender)
    if not options:
        return [], None, "", {"display": "none"}, {"display": "block"}
    valid = {o["value"] for o in options}
    new_voice = current_voice if (current_voice and current_voice in valid) else None
    return options, new_voice, "", {"display": "none"}, {"display": "block"}


# ── Reset preview when voice selection changes ────────────────────────────────
# filter_voices only fires on language/gender/store changes.  A different voice
# chosen within the same language+gender set also needs to clear the preview.

@app.callback(
    Output("preview-player", "src", allow_duplicate=True),
    Output("preview-player-wrapper", "style", allow_duplicate=True),
    Output("preview-voice-btn-wrapper", "style", allow_duplicate=True),
    Input("voice-select", "value"),
    prevent_initial_call=True,
)
def reset_preview_on_voice_change(voice):
    return "", {"display": "none"}, {"display": "block"}


# ── Voice preview ─────────────────────────────────────────────────────────────
# Synthesises a short language-appropriate phrase with the selected voice so
# the user can audition it before generating their real content.

@app.callback(
    Output("preview-player", "src"),
    Output("preview-player-wrapper", "style"),
    Output("preview-voice-btn-wrapper", "style"),
    Output("preview-voice-btn", "loading"),
    Input("preview-voice-btn", "n_clicks"),
    State("voice-select", "value"),
    State("language-select", "value"),
    State("gender-select", "value"),
    State("api-key-store", "data"),
    prevent_initial_call=True,
)
def preview_voice(n_clicks, voice_name, language_code, ssml_gender, api_key):
    if not n_clicks or not voice_name or not language_code:
        raise PreventUpdate

    key = (api_key or "").strip()
    if not key:
        raise PreventUpdate

    logger.info("preview_voice callback: voice=%s", voice_name)

    try:
        audio_b64 = preview_voice_uc.execute(
            voice_name=voice_name,
            language_code=language_code,
            ssml_gender=ssml_gender or "NEUTRAL",
            api_key=key,
        )
    except Exception as exc:
        logger.error("Voice preview failed: %s", exc)
        # Reset button loading state and hide preview player
        return "", {"display": "none"}, {"display": "block"}, False

    src = f"data:{AudioEncoding.MP3.mime};base64,{audio_b64}"
    return src, {"display": "block"}, {"display": "none"}, False


# ── Clientside: immediately show loading on preview-voice-btn click ───────────

app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            return true;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("preview-voice-btn", "loading", allow_duplicate=True),
    Input("preview-voice-btn", "n_clicks"),
    prevent_initial_call=True,
)
