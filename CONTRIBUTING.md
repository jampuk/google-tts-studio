# Contributing to Google Text-to-Speech Studio

First off, thank you for considering contributing to Google Text-to-Speech Studio! It's people like you that make this tool better for everyone.

This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

By participating in this project, you are expected to uphold a welcoming and inclusive environment. Please be respectful and considerate of others when communicating and collaborating.

## Getting Started

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/YOUR-USERNAME/google-tts-studio.git
    cd google-tts-studio
    ```
3.  **Set up the development environment**. Please refer to the [Getting Started section in the README](README.md#getting-started) for instructions on running the project locally with or without Docker.

## Development Guidelines

This project strictly adheres to **Clean Architecture** principles and specific coding rules.

### Folder Structure & Clean Architecture

All new code must be placed in the correct directory to maintain a predictable and organized repository structure:

*   `src/`: Contains the source code.
    *   `application/`: Presentation layer, use cases, and Dash callbacks.
    *   `domain/`: Core business models, validation, and pure functions.
    *   `adapters/`: Implementations of ports (e.g., API clients).
    *   `ports/`: Interfaces for external dependencies.
*   `tests/`: Contains all unit and integration tests, mirroring the structure of the `src` directory.

### Naming Conventions

*   All internal data structures, dictionary keys, and variables must strictly use `snake_case`.
*   Translation between external API formats and internal `snake_case` must be handled exclusively within the adapter layer.

## Testing and Linting

Before submitting a pull request, ensure that your code passes all tests and linting checks.

1.  **Run tests:**
    ```bash
    pytest tests/
    ```
    To run tests with coverage:
    ```bash
    pytest tests/ --cov=src
    ```

2.  **Run linter and type checker:**
    ```bash
    ruff check src/
    mypy src/
    ```

If you are adding new features, please include corresponding unit or integration tests in the `tests/` directory.

## Branching Strategy

1.  Create a new branch for your feature or bug fix from the `main` branch.
2.  Use descriptive branch names (e.g., `feature/add-new-voice-filter`, `bugfix/fix-audio-playback`).
    ```bash
    git checkout -b feature/your-feature-name
    ```

## Commit Messages

Write clear and concise commit messages. A good commit message should describe *what* changed and *why*.

*   Use the imperative mood (e.g., "Add feature" not "Added feature").
*   Keep the first line under 50 characters.
*   Add more detailed explanations in the body if necessary, wrapping lines at 72 characters.

## Pull Request Process

1.  Push your branch to your fork on GitHub.
    ```bash
    git push origin feature/your-feature-name
    ```
2.  Open a Pull Request (PR) against the `main` branch of the original repository.
3.  Provide a clear and descriptive title for your PR.
4.  In the PR description, explain the changes you made, why you made them, and any relevant context or issue numbers.
5.  Ensure that all CI checks (tests, linting) pass.
6.  A maintainer will review your PR and may provide feedback or request changes before merging.

Thank you for your contributions!
