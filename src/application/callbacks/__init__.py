# Importing each sub-module registers its Dash callbacks with the app instance.
# The order matters for callbacks that share allow_duplicate=True outputs —
# settings first (sets up stores), then voice, audio, history last.
from src.application.callbacks import (  # noqa: F401
    settings_callbacks,
    voice_callbacks,
    audio_callbacks,
    history_callbacks,
)
