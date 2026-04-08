"""Callbacks related to speech generation, character counting, and audio download."""
import base64
import logging

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from src.application.app import app, generate_speech_uc
from src.application.callbacks.helpers import err
from src.domain.models import AudioEncoding, sanitize_text, utf8_byte_length

logger = logging.getLogger(__name__)


# ── Character count ───────────────────────────────────────────────────────────

@app.callback(
    Output("char-count", "children"),
    Input("text-input", "value"),
    prevent_initial_call=False,
)
def update_char_count(text):
    raw = text or ""
    raw_chars = len(raw)
    clean = sanitize_text(raw)
    clean_chars = len(clean)
    clean_bytes = utf8_byte_length(clean)

    byte_suffix = f" ({clean_bytes} bytes)" if clean_bytes != clean_chars else ""

    if clean_chars != raw_chars:
        return f"{raw_chars} raw / {clean_chars} clean{byte_suffix} / 5000 byte limit"
    return f"{raw_chars} chars{byte_suffix} / 5000 byte limit"


# ── Clientside: immediately show loading state on generate-btn click ──────────

app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            return [true, true];
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("generate-btn", "loading", allow_duplicate=True),
    Output("generate-btn", "disabled", allow_duplicate=True),
    Input("generate-btn", "n_clicks"),
    prevent_initial_call=True,
)


# ── Generate speech ───────────────────────────────────────────────────────────

@app.callback(
    Output("current-audio-store", "data"),
    Output("history-store", "data"),
    Output("audio-player", "src"),
    Output("audio-player-card", "style"),
    Output("notification-area", "children"),
    Output("text-input", "value", allow_duplicate=True),
    Output("generate-btn", "loading"),
    Output("generate-btn", "disabled", allow_duplicate=True),
    Input("generate-btn", "n_clicks"),
    State("title-input", "value"),
    State("text-input", "value"),
    State("language-select", "value"),
    State("voice-select", "value"),
    State("gender-select", "value"),
    State("encoding-select", "value"),
    State("speaking-rate-slider", "value"),
    State("pitch-slider", "value"),
    State("volume-gain-slider", "value"),
    State("effects-profile-select", "value"),
    State("input-mode-toggle", "value"),
    State("api-key-store", "data"),
    State("history-store", "data"),
    prevent_initial_call=True,
)
def generate_speech(
    n_clicks, title, text, language_code, voice_name,
    ssml_gender, audio_encoding, speaking_rate, pitch,
    volume_gain_db, effects_profile_id, input_mode_value,
    api_key, history,
):
    if not n_clicks:
        raise PreventUpdate

    logger.info("generate_speech callback triggered, raw=%d chars", len(text or ""))

    try:
        result = generate_speech_uc.execute(
            text=text or "",
            language_code=language_code or "",
            voice_name=voice_name or "",
            ssml_gender=ssml_gender or "NEUTRAL",
            audio_encoding=audio_encoding or "MP3",
            speaking_rate=speaking_rate if speaking_rate is not None else 1.0,
            pitch=pitch if pitch is not None else 0.0,
            volume_gain_db=volume_gain_db if volume_gain_db is not None else 0.0,
            effects_profile_id=effects_profile_id or None,
            input_mode_value=input_mode_value or "text",
            api_key=api_key or "",
            title=title,
            history=list(history or []),
        )
    except ValueError as exc:
        logger.warning("generate_speech: validation error: %s", exc)
        return err(dmc.Notification(
            id="n-err",
            title="Error",
            message=str(exc)[:300],
            color="red",
            action="show",
        ))
    except Exception as exc:
        logger.error("generate_speech: unexpected error: %s", exc)
        return err(dmc.Notification(
            id="n-err",
            title="API Error",
            message=str(exc)[:300],
            color="red",
            action="show",
        ))

    # Build audio data URI using enum .mime attribute — no ENCODING_MIME dict needed
    encoding_enum = AudioEncoding.from_str(result.encoding)
    audio_src = f"data:{encoding_enum.mime};base64,{result.audio_content_b64}"

    current_audio = {
        "audio_content_b64": result.audio_content_b64,
        "encoding": result.encoding,
        "character_count": result.character_count,
        "title": result.safe_title,
    }

    if result.was_sanitized:
        msg = f"Text cleaned ({result.character_count} chars after cleaning)."
        color = "yellow"
        ntitle = "Text Cleaned"
    else:
        msg = f"Audio generated! ({result.character_count} chars)"
        color = "green"
        ntitle = "Success"

    notif = dmc.Notification(
        id="n-ok",
        title=ntitle,
        message=msg,
        color=color,
        action="show",
    )

    return (
        current_audio,
        result.history,
        audio_src,
        {"display": "block"},
        notif,
        result.clean_text,
        False,
        False,
    )


# ── Download audio ────────────────────────────────────────────────────────────

@app.callback(
    Output("audio-download", "data"),
    Input("download-btn", "n_clicks"),
    State("current-audio-store", "data"),
    prevent_initial_call=True,
)
def download_audio(n_clicks, current_audio):
    if not n_clicks or not current_audio:
        raise PreventUpdate
    b64_str = current_audio.get("audio_content_b64", "")
    encoding_str = current_audio.get("encoding", "MP3")
    title = current_audio.get("title", "tts_audio")

    # Use AudioEncoding enum's .mime and .ext — no ENCODING_EXT dict needed
    encoding_enum = AudioEncoding.from_str(encoding_str)
    safe_name = (
        "".join(c if c.isalnum() or c in "-_." else "_" for c in title).strip("_")
        or "tts_audio"
    )
    return dash.dcc.send_bytes(
        base64.b64decode(b64_str),
        filename=f"{safe_name}{encoding_enum.ext}",
        type=encoding_enum.mime,
    )
