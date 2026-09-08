# Google Text-to-Speech Studio

A full-featured web application for generating, playing, and downloading audio using the Google Cloud Text-to-Speech (TTS) API. Built with [Dash](https://dash.plotly.com/) and [Dash Mantine Components](https://www.dash-mantine-components.com/), following Clean Architecture principles.

## Features

- **Dynamic Voice Listing:** Automatically fetches the latest available voices (~60+ languages) directly from the Google TTS API, with intelligent filtering by language and gender.
- **Voice Preview:** Audition a voice with a short, language-appropriate phrase before generating your full text, saving API calls.
- **SSML Support:** Toggle between Plain Text and SSML input modes. Use SSML tags like `<break>`, `<prosody>`, and `<emphasis>` for fine-grained control over speech generation.
- **Text Sanitization & Validation:** Automatically strips HTML tags and Markdown syntax from plain text input. In SSML mode, validates XML structure before sending to the API. Check **Process text as-is** to bypass cleanup entirely and send the raw input directly to the API.
- **Byte-Accurate Limits:** Enforces the Google TTS API's 5000-byte limit (UTF-8), correctly handling multibyte characters (e.g., CJK, Arabic).
- **Advanced Audio Controls:** Fine-tune the generated speech with sliders for Speaking Rate, Pitch, and Volume Gain. Easily reset individual settings or all advanced settings to their defaults with dedicated reset buttons.
- **Device Profiles:** Apply audio effects optimized for specific devices (e.g., headphones, small Bluetooth speakers, large home entertainment systems).
- **Multiple Audio Formats:** Download generated audio in the exact format it was created (MP3, WAV/LINEAR16, OGG_OPUS, MULAW, or ALAW).
- **Light/Dark Mode:** Toggle between light and dark themes using the icon in the header. Your preference is saved automatically.
- **History & Export:** Keeps a history of your past up to 50 creations in the browser's local storage. You can instantly reload a past generation's exact voice settings, text, and title to generate it again. You can also export your history as a JSON file. (Note: The audio file itself is not stored in history to save browser storage space).
- **Data Management:** Easily clear all your saved settings, history, and API key with a single click.
- **Secure API Key Handling:** Your Google Cloud API key is stored securely in your browser's `localStorage` and is sent securely via HTTP headers.
- **Clean Architecture & Use Cases:** The codebase is structured into Application, Use Cases, Domain, Adapters, and Ports layers for maintainability and testability.
- **Resilient API Client:** Includes automatic retries with exponential backoff for transient network or API errors (e.g., rate limits).
- **In-Process Caching:** Reduces API calls by caching voice lists in-process.
- **Docker & Cloud Run Ready:** Includes a multi-stage Dockerfile (with linting and testing stages) and a `cloudbuild.yaml` for easy deployment to Google Cloud Run, complete with structured JSON logging, health checks, and dynamic worker scaling.

## Prerequisites

- Python 3.12+ (if running locally without Docker)
- Docker & Docker Compose (optional, for containerized development)
- A Google Cloud Platform account with the **Cloud Text-to-Speech API** enabled.
- A valid Google Cloud API Key.

## Getting Started

### 1. Obtain a Google Cloud API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Navigate to **APIs & Services > Library** and enable the **Cloud Text-to-Speech API**.
4. Go to **APIs & Services > Credentials** and create an **API key**.

### 2. Local Development (Without Docker)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd google-tts-studio
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Run the application:**
   ```bash
   python -m src.main
   ```

5. Open your browser and navigate to `http://localhost:8050`.

### 3. Local Development (With Docker Compose)

1. **Build and run the container:**
   ```bash
   docker compose up --build
   ```
   *Note: The default `docker-compose.yml` uses the `runtime` target for a production-like environment.*

2. Open your browser and navigate to `http://localhost:8050`.

3. **Run tests via Docker Compose:**
   ```bash
   docker compose run --rm tts-studio-test
   ```

## Usage

1. Open the application in your browser. Note that all controls are disabled by default.
2. The **🔑 API Configuration** accordion on the right sidebar will be open automatically if no key is saved.
3. Paste your Google Cloud API Key and click **Save Key**. The app will enable all controls, close the accordion, and automatically fetch the latest voice list.
4. (Optional) Enter a **Title** for your audio. This will be used as the filename when downloading and for easy identification in your history.
5. Choose your **Input Mode** (Plain Text or SSML) and enter your content in the main text area.
6. Select your desired Language, Gender, and Voice in the **Voice Settings** panel. The voice list dynamically updates based on your language and gender selections.
7. (Optional) Click **▶ Preview Voice** to hear a short sample of the selected voice.
8. Choose your preferred **Audio Format**.
9. (Optional) Expand **⚙ Advanced Settings** to adjust speed, pitch, volume, or apply an effects profile. You can reset individual settings or all advanced settings to their defaults using the **↺** buttons.
10. (Optional) Tick **Process text as-is (skip cleanup & fixes)** if your text is already clean and you do not want HTML tags, Markdown syntax, or whitespace to be stripped before synthesis. This option is hidden in SSML mode, where cleanup is never applied.
11. Click **🎙 Generate Speech**. The app will generate the audio and, unless bypass is enabled, automatically clean plain text of HTML/Markdown before synthesis. The character-count display reflects whether cleanup is active.
12. Once generated, you can play the audio directly in the browser or download it using the **⬇ Download Audio** button. The downloaded file will match the format selected during generation and use your provided title.
13. Your past creations will appear in the **Past Creations** table. Click **⤴ Load** on any row to instantly restore that generation's text, title, and full voice settings into the main interface, ready to be generated again. You can also selectively delete items using the **🗑** button, or export your entire history as a JSON file using the **⬇ Export JSON** button.
14. To wipe all data from your browser, open the **🔑 API Configuration** accordion and click **🗑 Clear Data**.

## Project Structure

The project strictly adheres to Clean Architecture principles, separating concerns into distinct layers:

```text
google-tts-studio/
├── src/
│   ├── main.py                     # Application entry point (Dash server)
│   ├── application/                # Presentation layer
│   │   ├── app.py                  # Dash app instance & DI container
│   │   ├── layout.py               # Dash Mantine Components UI definition
│   │   ├── use_cases/              # Application business rules
│   │   │   ├── fetch_voices.py     # Use case for retrieving voices
│   │   │   ├── generate_speech.py  # Use case orchestrating TTS generation
│   │   │   └── preview_voice.py    # Use case for voice auditioning
│   │   └── callbacks/              # Event handlers (Dash callbacks)
│   │       ├── audio_callbacks.py
│   │       ├── history_callbacks.py
│   │       ├── settings_callbacks.py
│   │       └── voice_callbacks.py
│   ├── domain/                     # Core business logic and data models
│   │   └── models.py               # Dataclasses, validation, and pure functions
│   ├── ports/                      # Interfaces for external dependencies
│   │   └── tts_port.py             # ITTSPort abstract base class
│   └── adapters/                   # Implementations of ports
│       ├── google_tts_adapter.py   # REST API client for Google TTS with retries
│       └── caching_tts_adapter.py  # Decorator adding TTL caching to ITTSPort
├── tests/                          # Unit and integration tests mirroring src/
├── Dockerfile                      # Multi-stage Docker build (builder, test, lint, runtime)
├── docker-compose.yml              # Local development environment
├── cloudbuild.yaml                 # CI/CD pipeline for Google Cloud Run
├── requirements.txt                # Production runtime dependencies
└── requirements-dev.txt            # Development and testing dependencies
```

## Running Tests & Linting

To run the test suite locally:

```bash
pytest tests/
```

To run tests with coverage:

```bash
pytest tests/ --cov=src
```

To run the linter and type checker (configured via `pyproject.toml`):

```bash
ruff check src/
mypy src/
```

## Deployment to Google Cloud Run

This project includes a `cloudbuild.yaml` file configured for automated deployment to Google Cloud Run using Google Cloud Build.

### Configuration Options

The `cloudbuild.yaml` supports several substitution variables:

- `_REGION`: GCP region (default: `us-central1`)
- `_SERVICE_NAME`: Cloud Run service name (default: `google-tts-studio`)
- `_ARTIFACT_REPO`: Artifact Registry repo name (default: `google-tts-studio`)
- `_ALLOW_UNAUTHENTICATED`: Set to `"true"` for public access, or `"false"` to require IAM authentication (default: `"true"`)
- `_WEB_CONCURRENCY`: Number of Gunicorn workers (default: `"3"`)

### Manual Deployment via Cloud Build

You can manually trigger a build and deployment using the `gcloud` CLI. 

**Important:** When running `gcloud builds submit` manually, the built-in `$COMMIT_SHA` variable is not automatically populated (unlike when triggered by a repository event). You must explicitly provide it via the `--substitutions` flag to prevent invalid image tag errors.

**PowerShell:**
```powershell
gcloud builds submit --config cloudbuild.yaml `
  --substitutions="COMMIT_SHA=$(git rev-parse HEAD),_REGION=us-central1,_SERVICE_NAME=google-tts-studio,_ARTIFACT_REPO=google-tts-studio,_ALLOW_UNAUTHENTICATED=true"
```

**cmd.exe:**
```cmd
for /f %i in ('git rev-parse HEAD') do set SHA=%i
gcloud builds submit --config cloudbuild.yaml --substitutions=COMMIT_SHA=%SHA%,_REGION=us-central1,_SERVICE_NAME=google-tts-studio,_ARTIFACT_REPO=google-tts-studio,_ALLOW_UNAUTHENTICATED=true
```

*(For ad-hoc testing, you can also use a placeholder string like `COMMIT_SHA=local-test`)*

*Ensure you have created the specified Artifact Registry repository (`google-tts-studio`) in your GCP project before running this command.*

### Automated CI/CD

You can connect your GitHub repository to Cloud Build in the Google Cloud Console and set up a trigger to automatically run the `cloudbuild.yaml` pipeline on every push to the `main` branch.

## Contributing

Contributions are welcome! Please read the [Contributing Guidelines](CONTRIBUTING.md) for details on our code of conduct, development workflow, and the process for submitting pull requests.

## License

This project is authored by **Jampuk Intelligence Systems** and is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.

## Disclaimer

This project was developed with the assistance of Artificial Intelligence (AI) tools to help with code generation, refactoring, and documentation. All AI-generated code has been reviewed, tested, and modified by human developers to ensure it meets our quality and architectural standards.