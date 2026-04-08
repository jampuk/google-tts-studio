"""Callbacks related to history rendering, loading, deletion, clearing, and export."""
import json
import logging
from datetime import datetime, timezone

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, ALL, ctx
from dash.exceptions import PreventUpdate

from src.application.app import app

logger = logging.getLogger(__name__)


# ── Clientside: immediately show loading on history-load-btn click ────────────

app.clientside_callback(
    """
    function(n_clicks_list) {
        var triggered = window.dash_clientside.callback_context.triggered;
        if (!triggered || triggered.length === 0) {
            return window.dash_clientside.no_update;
        }
        var prop_id = triggered[0].prop_id;
        if (!prop_id) return window.dash_clientside.no_update;
        var result = (n_clicks_list || []).map(function() {
            return window.dash_clientside.no_update;
        });
        var triggered_val = triggered[0].value;
        if (triggered_val) {
            var parts = prop_id.split('.');
            var id_str = parts[0];
            try {
                var id_obj = JSON.parse(id_str);
                if (window.dash_clientside.callback_context.inputs_list &&
                    window.dash_clientside.callback_context.inputs_list[0]) {
                    var inputs_list = window.dash_clientside.callback_context.inputs_list[0];
                    for (var i = 0; i < inputs_list.length; i++) {
                        var item = inputs_list[i];
                        if (item.id && item.id.index === id_obj.index) {
                            result[i] = true;
                            break;
                        }
                    }
                }
            } catch(e) {}
        }
        return result;
    }
    """,
    Output({"type": "history-load-btn", "index": ALL}, "loading", allow_duplicate=True),
    Input({"type": "history-load-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)


# ── Render history table ──────────────────────────────────────────────────────

@app.callback(
    Output("history-table", "children"),
    Input("history-store", "data"),
    prevent_initial_call=False,
)
def render_history_table(history):
    cols = ["Date/Time", "Title", "Text", "Format", "Actions"]
    thead = dmc.TableThead(dmc.TableTr([dmc.TableTh(c) for c in cols]))

    if not history:
        empty_row = dmc.TableTr([
            dmc.TableTd(
                "No history yet. Generate some speech!",
                style={"textAlign": "center", "color": "#aaa", "padding": "20px"},
            ),
        ] + [dmc.TableTd() for _ in range(4)])
        return [thead, dmc.TableTbody(empty_row)]

    rows = []
    for entry in history:
        ts = entry.get("timestamp", "")
        try:
            # Show date AND time so multi-day history is unambiguous (Flaw 4.7 fix)
            ts_display = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ts_display = ts[:19] if ts else "—"

        title_display = entry.get("title", "—")
        snippet = entry.get("text_snippet", "")[:60]
        if len(entry.get("text_snippet", "")) > 60:
            snippet += "…"
        encoding = entry.get("encoding", "MP3")
        eid = entry.get("id", "")

        row = dmc.TableTr([
            dmc.TableTd(ts_display, style={"whiteSpace": "nowrap"}),
            dmc.TableTd(
                dmc.Text(title_display, fw=500, size="sm"),
                style={"maxWidth": "120px", "overflow": "hidden"},
            ),
            dmc.TableTd(snippet, style={"maxWidth": "180px", "overflow": "hidden"}),
            dmc.TableTd(encoding),
            dmc.TableTd(dmc.Group([
                dmc.Button(
                    "⤴ Load",
                    id={"type": "history-load-btn", "index": eid},
                    size="xs",
                    variant="light",
                    color="violet",
                    loading=False,
                    loaderProps={"type": "dots"},
                ),
                dmc.Button(
                    "🗑",
                    id={"type": "history-delete-btn", "index": eid},
                    size="xs",
                    variant="subtle",
                    color="red",
                ),
            ], gap="xs")),
        ])
        rows.append(row)

    return [thead, dmc.TableTbody(rows)]


# ── Load history item ─────────────────────────────────────────────────────────
# Restores text, title, settings — including input_mode (Gap 2.7 fix).

@app.callback(
    Output("text-input", "value", allow_duplicate=True),
    Output("title-input", "value", allow_duplicate=True),
    Output("language-select", "value", allow_duplicate=True),
    Output("voice-select", "value", allow_duplicate=True),
    Output("gender-select", "value", allow_duplicate=True),
    Output("encoding-select", "value", allow_duplicate=True),
    Output("speaking-rate-slider", "value", allow_duplicate=True),
    Output("pitch-slider", "value", allow_duplicate=True),
    Output("volume-gain-slider", "value", allow_duplicate=True),
    Output("effects-profile-select", "value", allow_duplicate=True),
    Output("input-mode-toggle", "value", allow_duplicate=True),
    Output({"type": "history-load-btn", "index": ALL}, "loading"),
    Input({"type": "history-load-btn", "index": ALL}, "n_clicks"),
    State("history-store", "data"),
    prevent_initial_call=True,
)
def load_history_item(n_clicks_list, history):
    if not any(n for n in (n_clicks_list or []) if n):
        raise PreventUpdate
    triggered = ctx.triggered_id
    if not triggered:
        raise PreventUpdate

    all_loading_false = [False] * len(n_clicks_list or [])

    eid = triggered.get("index")
    for entry in (history or []):
        if entry.get("id") == eid:
            s = entry.get("settings", {})
            return (
                entry.get("full_text", ""),
                entry.get("title", ""),
                s.get("language_code", dash.no_update),
                s.get("voice_name", dash.no_update),
                s.get("ssml_gender", dash.no_update),
                s.get("audio_encoding", dash.no_update),
                s.get("speaking_rate", dash.no_update),
                s.get("pitch", dash.no_update),
                s.get("volume_gain_db", dash.no_update),
                s.get("effects_profile_id", dash.no_update),
                s.get("input_mode", "text"),   # Gap 2.7 fix: restore input mode
                all_loading_false,
            )
    raise PreventUpdate


# ── Delete single history item ────────────────────────────────────────────────

@app.callback(
    Output("history-store", "data", allow_duplicate=True),
    Input({"type": "history-delete-btn", "index": ALL}, "n_clicks"),
    State("history-store", "data"),
    prevent_initial_call=True,
)
def delete_history_item(n_clicks_list, history):
    if not any(n for n in (n_clicks_list or []) if n):
        raise PreventUpdate
    triggered = ctx.triggered_id
    if not triggered:
        raise PreventUpdate
    eid = triggered.get("index")
    return [e for e in (history or []) if e.get("id") != eid]


# ── Clear All History — opens confirmation modal (Gap 2.6 fix) ────────────────

@app.callback(
    Output("clear-all-history-modal", "opened"),
    Input("clear-history-btn", "n_clicks"),
    Input("clear-all-history-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_clear_all_history_modal(open_clicks, cancel_clicks):
    if ctx.triggered_id == "clear-history-btn":
        return True
    return False


@app.callback(
    Output("history-store", "data", allow_duplicate=True),
    Output("clear-all-history-modal", "opened", allow_duplicate=True),
    Input("clear-all-history-confirm-btn", "n_clicks"),
    prevent_initial_call=True,
)
def confirm_clear_all_history(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return [], False


# ── Export history as JSON ────────────────────────────────────────────────────

@app.callback(
    Output("history-download", "data"),
    Input("export-history-btn", "n_clicks"),
    State("history-store", "data"),
    prevent_initial_call=True,
)
def export_history(n_clicks, history):
    """Serialise the full history store to a pretty-printed JSON file download.

    The exported file contains all history entry fields (id, title, text_snippet,
    full_text, timestamp, encoding, settings) in the same format used by
    localStorage, making it easy to inspect, archive, or import into other tools.
    Audio content is intentionally excluded (as in the store itself).
    """
    if not n_clicks:
        raise PreventUpdate
    entries = list(history or [])
    payload = json.dumps(entries, indent=2, ensure_ascii=False)
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return dash.dcc.send_string(
        payload,
        filename=f"tts_history_{now}.json",
        type="application/json",
    )
