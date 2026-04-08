import dash

from src.ports.tts_port import ITTSPort
from src.adapters.google_tts_adapter import GoogleTTSAdapter
from src.adapters.caching_tts_adapter import CachingTTSAdapter
from src.application.use_cases.generate_speech import GenerateSpeechUseCase
from src.application.use_cases.fetch_voices import FetchVoicesUseCase
from src.application.use_cases.preview_voice import PreviewVoiceUseCase

app = dash.Dash(
    __name__,
    title="Google Text-to-Speech Studio",
    # suppress_callback_exceptions is required because the history load/delete
    # buttons use pattern-matching IDs ({"type": "history-load-btn", "index": ALL})
    # that are not present in the initial layout — Dash raises an exception for
    # those IDs unless this flag is set.  This is intentional, not a workaround.
    suppress_callback_exceptions=True,
    use_pages=False,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap"
    ],
)
server = app.server

# ── Dependency Injection ──────────────────────────────────────────────────────
# GoogleTTSAdapter is the concrete REST client.
# CachingTTSAdapter wraps it and serves list_voices() from an in-process cache
# (TTL: 1 hour) so voice-list API calls are not repeated on every page refresh.
# synthesize() is always delegated directly — audio is never cached.
#
# To swap implementations (e.g. for testing or to add a different backend),
# only these two lines need to change.
_raw_adapter: ITTSPort = GoogleTTSAdapter()
tts_adapter: ITTSPort = CachingTTSAdapter(_raw_adapter, ttl_seconds=3600)

# Use case instances are the DI units consumed by callbacks.
# Callbacks import these instances rather than the raw adapter, keeping all
# business logic encapsulated in the use case layer.
generate_speech_uc = GenerateSpeechUseCase(tts_adapter)
fetch_voices_uc = FetchVoicesUseCase(tts_adapter)
preview_voice_uc = PreviewVoiceUseCase(tts_adapter)


# ── Custom index string (splash screen) ──────────────────────────────────────
# Overrides Dash's default HTML shell to inject a full-screen splash overlay
# that is visible immediately on page load (replacing the default "Loading..."
# text) and fades out once React has populated #react-entry-point.
#
# The MutationObserver watches document.body for the moment that
# #react-entry-point gains more than one child element — at that point Dash has
# injected the real app component tree alongside the transient _dash-loading
# placeholder, which is the definitive "app is ready" signal.  The overlay is
# then faded out over 450 ms (via .pl-done CSS class) and removed from the DOM.
app.index_string = """<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>
      /* ── Page loader (splash screen) ───────────────────────────────────── */
      #page-loader {
        position: fixed;
        inset: 0;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: #ffffff;
        font-family: Inter, sans-serif;
        transition: opacity 0.45s ease;
      }

      /* Triggered by JS once React has hydrated — fades the overlay out */
      #page-loader.pl-done {
        opacity: 0;
        pointer-events: none;
      }

      .splash-body {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 16px;
        flex: 1;
      }

      .splash-icon {
        font-size: 56px;
        line-height: 1;
        animation: splash-pulse 2s ease-in-out infinite;
      }

      @keyframes splash-pulse {
        0%, 100% { transform: scale(1);   opacity: 1;    }
        50%       { transform: scale(1.1); opacity: 0.75; }
      }

      .splash-title {
        font-size: 24px;
        font-weight: 600;
        color: #1a1a2e;
        letter-spacing: -0.3px;
        text-align: center;
        padding: 0 24px;
      }

      /* Violet ring spinner — matches the app primaryColor */
      .splash-loader {
        margin-top: 8px;
        width: 40px;
        height: 40px;
        border: 3px solid #e9ecef;
        border-top-color: #7950f2;
        border-radius: 50%;
        animation: splash-spin 0.75s linear infinite;
      }

      @keyframes splash-spin {
        to { transform: rotate(360deg); }
      }

      .splash-footer {
        padding: 16px;
        font-size: 12px;
        color: #adb5bd;
        letter-spacing: 0.4px;
        text-align: center;
      }
    </style>
  </head>
  <body>
    <!-- Splash overlay — visible until Dash hydrates the layout -->
    <div id="page-loader">
      <div class="splash-body">
        <span class="splash-icon">🎙</span>
        <span class="splash-title">Google Text-to-Speech Studio</span>
        <div class="splash-loader"></div>
      </div>
      <div class="splash-footer">built by Beseek</div>
    </div>

    {%app_entry%}
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>

    <script>
        /* Remove the loader overlay once React has populated #react-entry-point.
           Uses MutationObserver so it works regardless of bundle download speed. */
        (function () {
            var loader = document.getElementById('page-loader');
            if (!loader) return;

            function dismiss() {
                loader.classList.add('pl-done');
                setTimeout(function () {
                    if (loader.parentNode) { loader.parentNode.removeChild(loader); }
                }, 450);
            }

            /* Already mounted? Dismiss immediately. */
            var ep = document.getElementById('react-entry-point');
            if (ep && ep.childElementCount > 1) { dismiss(); return; }

            var obs = new MutationObserver(function () {
                var ep = document.getElementById('react-entry-point');
                if (ep && ep.childElementCount > 1) {
                    obs.disconnect();
                    dismiss();
                }
            });
            obs.observe(document.body, { childList: true, subtree: true });
        })();
    </script>
  </body>
</html>"""


# ── Health-check endpoint ─────────────────────────────────────────────────────
# Cloud Run (and any load balancer) can probe /healthz for a fast, lightweight
# liveness check without triggering a full Dash page render.
@server.route("/healthz")
def healthz():
    return {"status": "ok"}, 200
