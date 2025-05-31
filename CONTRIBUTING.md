# Contributing to Books-to-Anki

First off, thank you for considering contributing to Books-to-Anki! Your help is appreciated.

This document provides guidelines for contributing to this project.

## How to Contribute

We welcome contributions in various forms, including:

*   Reporting bugs
*   Suggesting new features or enhancements
*   Improving documentation
*   Writing code to fix bugs or implement new features

## Getting Started

1.  **Fork the Repository**: Start by forking the main repository to your own GitHub account.
2.  **Clone Your Fork**: Clone your forked repository to your local machine:
    ```bash
    git clone https://github.com/YOUR_USERNAME/books-to-anki.git
    cd books-to-anki
    ```
3.  **Set Up Your Environment**: This project uses `uv` for environment and package management, and a `Makefile` for common development tasks.
    *   Ensure `uv` is installed. If not, you can typically install it by following the instructions at [astral.sh/uv](https://astral.sh/uv). The `Makefile` also includes a `uv` target that attempts to install it.
    *   Set up the virtual environment and install dependencies:
        ```bash
        make setup
        ```
    *   To install the package in editable mode (recommended for development):
        ```bash
        make install-edit
        ```

## Development Process

### Branches

*   Create a new branch for each feature or bug fix:
    ```bash
    git checkout -b your-feature-name
    ```
    Or for a bug fix:
    ```bash
    git checkout -b fix/issue-description
    ```
*   Base your branches off the `main` branch.

### Coding Standards

*   **Linting**: This project uses `ruff` for linting. Before committing your changes, please run the linter:
    ```bash
    make lint
    ```
    Address any issues reported by the linter.
*   **Docstrings and Comments**: Write clear and concise docstrings for all modules, classes, and functions. Comment complex or non-obvious code sections.
*   **Type Hinting**: Use Python type hints for function signatures and variables where appropriate.

### Testing

*   This project uses `pytest` for testing. Ensure all existing tests pass and add new tests for any new functionality or bug fixes.
*   To run tests:
    ```bash
    make test
    ```
    This will also generate a coverage report (`coverage.xml`). Aim to maintain or increase test coverage.

### Committing

*   Write clear and descriptive commit messages.
*   Reference any relevant issue numbers in your commit messages (e.g., `Fixes #123`).

## Understanding the Project

This section provides a high-level overview of the project's structure and the technologies used.

### Project Structure

*   **`src/`**: Contains the source code for the tools.
    *   `book_to_flashcards/`: Code for the `book-to-flashcard` tool.
    *   `book_complexity/`: Code for the `book-complexity` and `books-complexity` tools.
    *   `split_sentences/`: Contains logic for sentence splitting used by `book-to-flashcard`.
*   **`test/`**: Contains tests for the project (using `pytest` and `pytest-testmon`).
*   **`data/`**: Used for storing sample data
*   **`Makefile`**: Defines common development tasks. Key targets include:
    *   `setup`: Installs dependencies using `uv`.
    *   `install`: Installs the package (suitable for quick checks, but `install-edit` is needed for development).
    *   `install-edit`: Installs the package in editable mode.
    *   `lint`: Runs `ruff` for linting.
    *   `test`: Runs `pytest` with coverage.
    *   `profile`: Runs profiling using `kernprof` and `line_profiler`.
    *   `dist`: Builds the distributable package using `pyproject-build`.
    *   **Note on Makefile Usage**: Developers should rely on the `Makefile` for common tasks like linting, testing, and building. The GitHub Actions build also delegates to the Makefile. This ensures consistency and avoids the need to memorize manual command-line steps.
*   **`pyproject.toml`**:
    *   Defines project metadata, dependencies, and build system configuration.
    *   Defines entry points for the command-line scripts: `book-to-flashcard`, `book-complexity`, `books-complexity`.
*   **`readme.md`**: Provides detailed user-facing documentation.

### Key Technologies & Dependencies

*   Python (e.g., Python 3.9 as specified in `pyproject.toml`)
*   `uv`: For package management, environment setup, and task running.
*   `spacy`: For natural language processing (sentence splitting, grammatical analysis).
*   `DeepL API`: For translation.
*   `Anki` (external application): The primary target for flashcard output.
*   `Click`: For creating command-line interfaces.
*   `genanki`: For programmatically creating Anki decks.
*   `ruff`: For linting and code formatting.
*   `pytest`: For testing.
*   `pytest-testmon` & `pytest-cov`: For optimizing test runs and coverage reporting.
*   `mypy`: For static type checking (listed as a dev dependency).

## Submitting Changes

1.  **Push to Your Fork**: Push your changes to your forked repository:
    ```bash
    git push origin your-feature-name
    ```
2.  **Create a Pull Request (PR)**:
    *   Go to the original `books-to-anki` repository on GitHub.
    *   You should see a prompt to create a Pull Request from your recently pushed branch.
    *   Ensure your PR has a clear title and description. Explain the changes you've made and why.
    *   Link any relevant issues in your PR description.
    *   Ensure all automated checks (like GitHub Actions, if configured) pass.
3.  **Code Review**: Your PR will be reviewed. Be prepared to address any feedback or make further changes.

## Building the Package

To build the distributable package (e.g., for a release):

```bash
make dist
```
This will create the package files in the `dist/` directory.

## Reporting Bugs or Suggesting Features

*   Use the GitHub Issues section of the main repository to report bugs or suggest new features.
*   For bugs, please provide:
    *   A clear description of the bug.
    *   Steps to reproduce the bug.
    *   Your operating system and Python version.
    *   Any relevant error messages or screenshots.
*   For feature requests, clearly explain the proposed feature and its benefits.

Thank you again for your contribution! 