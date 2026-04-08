import logging
import os

# ── Logging configuration ─────────────────────────────────────────────────────
# When LOG_FORMAT=json (set automatically in Cloud Run / Docker), emit
# structured JSON logs that Google Cloud Logging can parse natively.
# Fields are renamed to match the Cloud Logging structured log schema:
#   "severity"  ← levelname   (enables log-level filtering in Cloud Console)
#   "time"      ← asctime      (ISO timestamp)
#
# In any other environment (local dev, CI) plain-text output is used so
# human-readable tracebacks are not cluttered with JSON encoding.
#
# Must be configured BEFORE any module import so all child loggers inherit
# the handler and formatter set here.

_LOG_FORMAT = os.environ.get("LOG_FORMAT", "text").lower()

if _LOG_FORMAT == "json":
    from pythonjsonlogger import jsonlogger  # type: ignore[import]

    _handler = logging.StreamHandler()
    _handler.setFormatter(
        jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={
                "levelname": "severity",
                "asctime": "time",
                "name": "logger",
            },
        )
    )
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(_handler)
else:
    # Plain text — clear and readable during local development / pytest runs.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

from src.application.app import app, server  # noqa: F401 — server re-exported for gunicorn
from src.application import layout
from src.application import callbacks  # noqa: F401 — registers all callback sub-modules

app.layout = layout.create_layout()

if __name__ == "__main__":
    app.run(debug=True, port=8050)
