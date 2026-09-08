import dash_mantine_components as dmc
from dash import dcc, html


# ──────────────────────────────────────────────
# Voice / Language data
# ──────────────────────────────────────────────
# Language and voice lists start empty.  They are populated at runtime by the
# fetch_voices / update_language_options / filter_voices callbacks after the
# user supplies an API key.  Static hardcoded lists were removed because they
# silently go stale as Google adds or retires voices.

EFFECTS_PROFILE_OPTIONS = [
    {"value": "headphone-class-device", "label": "Headphone"},
    {"value": "small-bluetooth-speaker-class-device", "label": "Small Bluetooth Speaker"},
    {"value": "medium-bluetooth-speaker-class-device", "label": "Medium Bluetooth Speaker"},
    {"value": "handset-class-device", "label": "Handset"},
    {"value": "large-home-entertainment-class-device", "label": "Large Home Entertainment"},
    {"value": "large-automotive-class-device", "label": "Large Automotive"},
    {"value": "telephony-class-application", "label": "Telephony"},
]

SPEAKING_RATE_MARKS = [
    {"value": 0.25, "label": "0.25×"},
    {"value": 1.0, "label": "1×"},
    {"value": 2.0, "label": "2×"},
    {"value": 4.0, "label": "4×"},
]

PITCH_MARKS = [
    {"value": -20, "label": "-20"},
    {"value": 0, "label": "0"},
    {"value": 20, "label": "+20"},
]

VOLUME_MARKS = [
    {"value": -96, "label": "-96"},
    {"value": 0, "label": "0"},
    {"value": 16, "label": "+16"},
]


def create_layout() -> dmc.MantineProvider:
    """Build and return the full application layout."""

    github_star_btn = html.A(
        dmc.Group(
            [
                # GitHub mark (hosted by GitHub assets CDN)
                html.Img(
                    src="https://github.githubassets.com/favicons/favicon.png",
                    style={"width": "16px", "height": "16px", "flexShrink": 0, "borderRadius": "3px"},
                ),
                # Star icon (⭐)
                html.Span(
                    "★",
                    style={"fontSize": "13px", "lineHeight": 1},
                ),
                dmc.Text(
                    "Star",
                    size="sm",
                    fw=500,
                    style={"lineHeight": 1},
                    visibleFrom="xs",
                ),
            ],
            gap=5,
            align="center",
            wrap="nowrap",
        ),
        href="https://github.com/beseekapp/google-tts-studio",
        target="_blank",
        rel="noopener noreferrer",
        style={
            "display": "inline-flex",
            "alignItems": "center",
            "padding": "5px 12px",
            "borderRadius": "6px",
            "border": "1px solid #d0d7de",
            "background": "linear-gradient(180deg, #f6f8fa 0%, #ebf0f4 100%)",
            "color": "#24292f",
            "textDecoration": "none",
            "fontFamily": "Inter, sans-serif",
            "cursor": "pointer",
            "transition": "background 0.15s, border-color 0.15s, box-shadow 0.15s",
            "boxShadow": "0 1px 0 rgba(27,31,36,0.04)",
            "whiteSpace": "nowrap",
        },
        id="github-star-btn",
    )

    header = dmc.AppShellHeader(
        dmc.Group(
            [
                dmc.Text("🎙", size="xl"),
                dmc.Text(
                    "Google Text-to-Speech Studio",
                    fw=600,
                    size="lg",
                    style={"fontFamily": "Inter, sans-serif"},
                    visibleFrom="sm",
                ),
                dmc.Text(
                    "TTS Studio",
                    fw=600,
                    size="md",
                    style={"fontFamily": "Inter, sans-serif"},
                    hiddenFrom="sm",
                ),
                dmc.Group(
                    [
                        github_star_btn,
                        dmc.ActionIcon(
                            "🌙",
                            id="dark-mode-toggle",
                            variant="subtle",
                            size="lg",
                        ),
                    ],
                    gap="xs",
                    ml="auto",
                    align="center",
                    wrap="nowrap",
                ),
            ],
            h="100%",
            px="md",
            gap="xs",
        ),
        style={"borderBottom": "1px solid #e9ecef"},
    )

    # ── Left column ──────────────────────────────────────────────────────────

    text_input_card = dmc.Paper(
        dmc.Stack(
            [
                dmc.TextInput(
                    id="title-input",
                    label="Title",
                    placeholder="Enter a title (used as filename and in history)...",
                    disabled=True,
                ),
                # ── Input mode toggle ────────────────────────────────────────
                dmc.Group(
                    [
                        dmc.Text("Input Mode", size="sm", fw=500),
                        dmc.SegmentedControl(
                            id="input-mode-toggle",
                            value="text",
                            data=[
                                {"value": "text", "label": "Plain Text"},
                                {"value": "ssml", "label": "SSML"},
                            ],
                            size="xs",
                            disabled=True,
                        ),
                    ],
                    justify="space-between",
                    align="center",
                ),
                # Bypass cleanup checkbox — shown only in plain-text mode.
                # Uses dcc.Checklist (not dmc.Checkbox) because dmc.Checkbox's
                # 'checked' prop is not reliably dispatched by the Dash callback
                # graph in DMC >=0.14.  dcc.Checklist.value is stable and works.
                html.Div(
                    dcc.Checklist(
                        id="bypass-cleanup-checkbox",
                        options=[{"label": " Process text as-is (skip cleanup & fixes)", "value": "bypass"}],
                        value=[],
                        style={"fontSize": "14px"},
                    ),
                    id="bypass-cleanup-checkbox-wrapper",
                ),
                # SSML hint — shown only when SSML mode is active.
                # Wrapped in a plain div so the callback toggles display on the
                # div, not on the dmc.Alert directly (avoids observer-helper.js
                # getLowerCaseAttribute TypeError in DMC's internal DOM walker).
                html.Div(
                    dmc.Alert(
                        id="ssml-hint",
                        title="SSML Mode",
                        color="blue",
                        variant="light",
                        children=(
                            "Wrap your content in <speak>…</speak>. "
                            "Supported tags: <break time=\"500ms\"/>, "
                            "<prosody rate=\"slow\">, <emphasis level=\"strong\">, "
                            "<say-as interpret-as=\"characters\">. "
                            "Note: pitch customisation is ignored on Neural2/Studio voices."
                        ),
                    ),
                    id="ssml-hint-wrapper",
                    style={"display": "none"},
                ),
                dmc.Textarea(
                    id="text-input",
                    label="Text Content",
                    placeholder="Enter text to convert to speech...",
                    minRows=8,
                    autosize=True,
                    maxRows=20,
                    disabled=True,
                ),
                dmc.Group(
                    [
                        dmc.Text(id="char-count", size="sm", c="dimmed",
                                 children="0 chars / 5000 byte limit"),
                        dmc.Button(
                            "🎙 Generate Speech",
                            id="generate-btn",
                            variant="filled",
                            disabled=True,
                            loading=False,
                            loaderProps={"type": "dots"},
                        ),
                    ],
                    justify="space-between",
                    mt="xs",
                ),
            ]
        ),
        shadow="sm",
        p="md",
        radius="md",
    )

    audio_player_card = dmc.Paper(
        dmc.Stack(
            [
                dmc.Text("Audio Output", fw=600),
                html.Audio(
                    id="audio-player",
                    controls=True,
                    style={"width": "100%"},
                ),
                dmc.Button(
                    "⬇ Download Audio",
                    id="download-btn",
                    variant="outline",
                    disabled=True,
                ),
                html.Div(id="notification-area"),
            ]
        ),
        shadow="sm",
        p="md",
        radius="md",
        id="audio-player-card",
        style={"display": "none"},
    )

    history_card = dmc.Paper(
        dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Text("Past Creations", fw=600),
                        dmc.Group(
                            [
                                dmc.Button(
                                    "⬇ Export JSON",
                                    id="export-history-btn",
                                    variant="subtle",
                                    color="blue",
                                    size="xs",
                                ),
                                dmc.Button(
                                    "🗑 Clear All",
                                    id="clear-history-btn",
                                    variant="subtle",
                                    color="red",
                                    size="xs",
                                ),
                            ],
                            gap="xs",
                        ),
                    ],
                    justify="space-between",
                ),
                dmc.ScrollArea(
                    dmc.Table(
                        id="history-table",
                        striped=True,
                        highlightOnHover=True,
                        children=[],
                    ),
                    h={"base": 180, "sm": 240, "md": 300},
                ),
            ]
        ),
        shadow="sm",
        p="md",
        radius="md",
    )

    left_col = dmc.GridCol(
        dmc.Stack(
            [text_input_card, audio_player_card, history_card],
            gap="md",
        ),
        span={"base": 12, "md": 8},
        order={"base": 2, "md": 1},
    )

    # ── Right column ─────────────────────────────────────────────────────────

    voice_settings_card = dmc.Paper(
        dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Text("Voice Settings", fw=600),
                        dmc.Badge(
                            id="voice-count-badge",
                            children="0 voices",
                            color="violet",
                            variant="light",
                            size="sm",
                        ),
                    ],
                    justify="space-between",
                    mb="sm",
                ),
                # Row 1: Language — populated at runtime by fetch_voices callback
                dmc.Select(
                    id="language-select",
                    label="Language",
                    searchable=True,
                    data=[],
                    value=None,
                    placeholder="Select language...",
                    disabled=True,
                ),
                # Row 2: Gender (filter before seeing voice list)
                html.Div(
                    dmc.Select(
                        id="gender-select",
                        label="Gender",
                        data=[
                            {"value": "ALL", "label": "All Genders"},
                            {"value": "FEMALE", "label": "FEMALE ♀"},
                            {"value": "MALE", "label": "MALE ♂"},
                            {"value": "NEUTRAL", "label": "NEUTRAL ⚥"},
                        ],
                        value=None,
                        placeholder="Select gender...",
                        disabled=True,
                    ),
                    id="gender-select-wrapper",
                    style={"borderRadius": "8px", "transition": "box-shadow 0.3s"},
                ),
                # Row 3: Voice list — populated at runtime by filter_voices callback
                html.Div(
                    dmc.Select(
                        id="voice-select",
                        label="Voice",
                        searchable=True,
                        data=[],
                        value=None,
                        placeholder="Select voice...",
                        disabled=True,
                    ),
                    id="voice-select-wrapper",
                    style={"borderRadius": "8px", "transition": "box-shadow 0.3s"},
                ),
                # Row 3b: Voice preview.
                # Wrapper div toggled by callbacks instead of the dmc.Button's
                # style directly — prevents the observer-helper.js TypeError.
                html.Div(
                    dmc.Button(
                        "▶ Preview Voice",
                        id="preview-voice-btn",
                        size="xs",
                        variant="light",
                        color="teal",
                        disabled=True,
                        fullWidth=False,
                        loading=False,
                        loaderProps={"type": "dots"},
                    ),
                    id="preview-voice-btn-wrapper",
                ),
                # Preview audio player — wrapped in a plain div so the callback
                # toggles the div's display, never html.Audio's style directly
                # (avoids the observer-helper.js getLowerCaseAttribute TypeError).
                html.Div(
                    html.Audio(
                        id="preview-player",
                        controls=True,
                        style={"width": "100%"},
                    ),
                    id="preview-player-wrapper",
                    style={"display": "none"},
                ),
                # Row 4: Audio Format
                html.Div(
                    dmc.Select(
                        id="encoding-select",
                        label="Audio Format",
                        data=["MP3", "LINEAR16", "OGG_OPUS", "MULAW", "ALAW"],
                        value=None,
                        placeholder="Select format...",
                        disabled=True,
                    ),
                    id="encoding-select-wrapper",
                    style={"borderRadius": "8px", "transition": "box-shadow 0.3s"},
                ),
            ],
            gap="sm",
        ),
        shadow="sm",
        p="md",
        radius="md",
    )

    advanced_settings_accordion = dmc.Accordion(
        dmc.AccordionItem(
            [
                dmc.AccordionControl("⚙ Advanced Settings"),
                dmc.AccordionPanel(
                    dmc.Stack(
                        [
                            # ── Reset All row ──────────────────────────────
                            dmc.Group(
                                [
                                    dmc.Text("Advanced Settings", size="sm", c="dimmed"),
                                    dmc.Button(
                                        "↺ Reset All",
                                        id="reset-all-advanced-btn",
                                        size="xs",
                                        variant="subtle",
                                        color="gray",
                                        disabled=True,
                                    ),
                                ],
                                justify="space-between",
                                mb="xs",
                            ),
                            # ── Speaking Rate ──────────────────────────────
                            dmc.Group(
                                [
                                    dmc.Text("Speaking Rate", size="sm", fw=500),
                                    dmc.ActionIcon(
                                        "↺",
                                        id="reset-speaking-rate-btn",
                                        size="xs",
                                        variant="subtle",
                                        color="gray",
                                        disabled=True,
                                    ),
                                ],
                                justify="space-between",
                                gap="xs",
                            ),
                            dmc.Slider(
                                id="speaking-rate-slider",
                                min=0.25,
                                max=4.0,
                                step=0.05,
                                value=1.0,
                                marks=SPEAKING_RATE_MARKS,
                                mb="xl",
                                disabled=True,
                                # updatemode="blur" fires the callback only on
                                # mouseup/touchend, preventing rapid localStorage
                                # writes during a drag gesture.
                                updatemode="blur",
                            ),
                            # ── Pitch ──────────────────────────────────────
                            dmc.Group(
                                [
                                    dmc.Group(
                                        [
                                            dmc.Text("Pitch", size="sm", fw=500),
                                            dmc.Popover(
                                                [
                                                    dmc.PopoverTarget(
                                                        dmc.ActionIcon(
                                                            "i",
                                                            size="xs",
                                                            variant="outline",
                                                            color="blue",
                                                        )
                                                    ),
                                                    dmc.PopoverDropdown(
                                                        dmc.Text(
                                                            "⚠ Not all voices support custom pitch. "
                                                            "Neural2 and Studio voices ignore this setting — "
                                                            "only Standard and WaveNet voices honour it.",
                                                            size="xs",
                                                            style={"maxWidth": 260},
                                                        )
                                                    ),
                                                ],
                                                width=270,
                                                position="top",
                                                withArrow=True,
                                                shadow="md",
                                            ),
                                        ],
                                        gap=4,
                                        align="center",
                                    ),
                                    dmc.ActionIcon(
                                        "↺",
                                        id="reset-pitch-btn",
                                        size="xs",
                                        variant="subtle",
                                        color="gray",
                                        disabled=True,
                                    ),
                                ],
                                justify="space-between",
                                gap="xs",
                            ),
                            dmc.Slider(
                                id="pitch-slider",
                                min=-20,
                                max=20,
                                step=0.5,
                                value=0,
                                marks=PITCH_MARKS,
                                mb="xl",
                                disabled=True,
                                updatemode="blur",
                            ),
                            # ── Volume Gain ────────────────────────────────
                            dmc.Group(
                                [
                                    dmc.Text("Volume Gain (dB)", size="sm", fw=500),
                                    dmc.ActionIcon(
                                        "↺",
                                        id="reset-volume-gain-btn",
                                        size="xs",
                                        variant="subtle",
                                        color="gray",
                                        disabled=True,
                                    ),
                                ],
                                justify="space-between",
                                gap="xs",
                            ),
                            dmc.Slider(
                                id="volume-gain-slider",
                                min=-96,
                                max=16,
                                step=1,
                                value=0,
                                marks=VOLUME_MARKS,
                                mb="xl",
                                disabled=True,
                                updatemode="blur",
                            ),
                            # ── Effects Profile ────────────────────────────
                            dmc.Group(
                                [
                                    dmc.Text("Effects Profile", size="sm", fw=500),
                                    dmc.ActionIcon(
                                        "↺",
                                        id="reset-effects-profile-btn",
                                        size="xs",
                                        variant="subtle",
                                        color="gray",
                                        disabled=True,
                                    ),
                                ],
                                justify="space-between",
                                gap="xs",
                            ),
                            dmc.Select(
                                id="effects-profile-select",
                                clearable=True,
                                data=EFFECTS_PROFILE_OPTIONS,
                                placeholder="None",
                                disabled=True,
                            ),
                        ],
                        gap="xs",
                    )
                ),
            ],
            value="advanced",
        ),
        radius="md",
    )

    api_key_accordion = dmc.Accordion(
        dmc.AccordionItem(
            [
                dmc.AccordionControl("🔑 API Configuration"),
                dmc.AccordionPanel(
                    dmc.Stack(
                        [
                            dmc.Textarea(
                                id="api-key-input",
                                label="Google Cloud API Key",
                                placeholder="Paste your Google Cloud TTS API key here...",
                                minRows=3,
                                description=(
                                    "Your key is stored only in browser localStorage "
                                    "and never sent to any server other than Google."
                                ),
                            ),
                            dmc.Group(
                                [
                                    dmc.Button(
                                        "Save Key",
                                        id="save-api-key-btn",
                                        size="xs",
                                        variant="outline",
                                    ),
                                    dmc.Button(
                                        "🔄 Refresh Voices",
                                        id="refresh-voices-btn",
                                        size="xs",
                                        variant="light",
                                        color="violet",
                                        disabled=True,
                                    ),
                                    dmc.Button(
                                        "🗑 Clear Data",
                                        id="clear-data-btn",
                                        size="xs",
                                        variant="subtle",
                                        color="red",
                                    ),
                                ],
                                gap="xs",
                            ),
                            dmc.Text(
                                id="api-key-status",
                                size="xs",
                                c="dimmed",
                                children="",
                            ),
                        ],
                        gap="xs",
                    )
                ),
            ],
            value="api-key",
        ),
        id="api-key-accordion",
        value=None,
        radius="md",
    )

    right_col = dmc.GridCol(
        dmc.Stack(
            [voice_settings_card, advanced_settings_accordion, api_key_accordion],
            gap="md",
        ),
        span={"base": 12, "md": 4},
        order={"base": 1, "md": 2},
    )

    # ── Clear All History Confirmation Modal ──────────────────────────────────

    clear_all_history_modal = dmc.Modal(
        id="clear-all-history-modal",
        title=dmc.Group(
            [dmc.Text("⚠", size="xl"), dmc.Text("Clear All History", fw=700)],
            gap="xs",
        ),
        children=[
            dmc.Text(
                "This will permanently delete all past creations from your history.",
                mb="xs",
            ),
            dmc.Text(
                "This action cannot be undone.",
                c="red",
                fw=500,
                mb="lg",
            ),
            dmc.Group(
                [
                    dmc.Button(
                        "Cancel",
                        id="clear-all-history-cancel-btn",
                        variant="outline",
                    ),
                    dmc.Button(
                        "Yes, Clear History",
                        id="clear-all-history-confirm-btn",
                        color="red",
                    ),
                ],
                justify="flex-end",
                gap="sm",
            ),
        ],
        opened=False,
        centered=True,
        withCloseButton=True,
    )

    # ── Clear Data Confirmation Modal ─────────────────────────────────────────

    clear_data_modal = dmc.Modal(
        id="clear-data-modal",
        title=dmc.Group(
            [dmc.Text("⚠", size="xl"), dmc.Text("Clear All App Data", fw=700)],
            gap="xs",
        ),
        children=[
            dmc.Text(
                "This will permanently delete:",
                mb="xs",
            ),
            dmc.List(
                [
                    dmc.ListItem("Your saved API key"),
                    dmc.ListItem("All voice & audio settings"),
                    dmc.ListItem("Your entire generation history (including audio)"),
                ],
                mb="md",
            ),
            dmc.Text(
                "This action cannot be undone.",
                c="red",
                fw=500,
                mb="lg",
            ),
            dmc.Group(
                [
                    dmc.Button(
                        "Cancel",
                        id="clear-data-cancel-btn",
                        variant="outline",
                    ),
                    dmc.Button(
                        "Yes, Clear Everything",
                        id="clear-data-confirm-btn",
                        color="red",
                    ),
                ],
                justify="flex-end",
                gap="sm",
            ),
        ],
        opened=False,
        centered=True,
        withCloseButton=True,
    )

    # ── Stores & Download ─────────────────────────────────────────────────────

    stores = html.Div(
        [
            dcc.Store(id="settings-store", storage_type="local"),
            dcc.Store(id="history-store", storage_type="local", data=[]),
            dcc.Store(id="current-audio-store", storage_type="memory"),
            dcc.Store(id="api-key-store", storage_type="local"),
            # voices-store uses session storage so voices are re-fetched on new tabs
            # but cached within the same browser session (avoids re-fetching on every
            # callback yet still reflects API changes on refresh).
            dcc.Store(id="voices-store", storage_type="session", data=[]),
            dcc.Download(id="audio-download"),
            dcc.Download(id="history-download"),
            # One-shot interval fires once on page load to trigger auto-fetch of voices
            dcc.Interval(id="startup-interval", interval=500, max_intervals=1, n_intervals=0),
            dcc.Store(id="color-scheme-store", storage_type="local", data="light"),
        ]
    )

    # ── Assemble ──────────────────────────────────────────────────────────────

    app_shell = dmc.AppShell(
        [
            header,
            dmc.AppShellMain(
                dmc.Container(
                    dmc.Grid(
                        [right_col, left_col],
                        gutter="md",
                    ),
                    size="xl",
                    py="md",
                )
            ),
        ],
        header={"height": 60},
        padding={"base": "xs", "sm": "md"},
    )

    return dmc.MantineProvider(
        [
            dmc.NotificationProvider(position="top-right"),
            app_shell,
            stores,
            clear_data_modal,
            clear_all_history_modal,
        ],
        id="mantine-provider",
        forceColorScheme="light",
        theme={"primaryColor": "violet", "fontFamily": "Inter, sans-serif"},
    )
