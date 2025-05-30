# Repository Overview: books-to-anki

This repository contains Python tools designed to aid in language learning by processing books and other text materials. It offers functionalities to convert texts into Anki flashcards and to analyze text complexity.

## Core Functionalities

The repository is structured around two main tools:

1.  **`book-to-flashcard`**:
    *   Converts text files into Anki flashcard decks (.apkg files).
    *   Splits text into manageable chunks using AI language parsing (via `spacy`).
    *   Translates chunks using DeepL API.
    *   Allows intermediate JSONL format for staged processing (e.g., process text, then translate separately, or generate multiple output formats from a single translation).
    *   Includes a dummy translation option for testing without translation API usage.

2.  **`books-complexity` / `book-complexity`**:
    *   Calculates various complexity metrics for text files.
    *   Metrics include: word count, sentence count, words per sentence, mean word length, mean grammar depth (based on `spacy` parse trees).
    *   Can estimate "words known" and "percent words known" if a list of known words is provided (e.g., from AnkiMorphs).
    *   Provides a "Vocabulary Level" based on word frequency lists, very vaguely corresponding to CEFR levels.

## Project Structure

*   **`src/`**: Contains the source code for the tools.
    *   `book_to_flashcards/`: Code for the `book-to-flashcard` tool.
    *   `book_complexity/`: Code for the `book-complexity` and `books-complexity` tools.
    *   `split_sentences/`: Contains logic for sentence splitting used by `book-to-flashcard`.
*   **`test/`**: Contains tests for the project (using `pytest` and `pytest-testmon`).
*   **`data/`**: Likely used for storing sample data, test files, or user-generated content.
*   **`Makefile`**: Defines common development tasks such as:
    *   `setup`: Installs dependencies using `uv`.
    *   `install`: Installs the package.
    *   `lint`: Runs `ruff` for linting.
    *   `test`: Runs `pytest` with coverage.
    *   `profile`: Runs profiling using `kernprof` and `line_profiler`.
    *   `dist`: Builds the distributable package using `pyproject-build`.
*   **`pyproject.toml`**:
    *   Defines project metadata, dependencies, and build system configuration.
    *   Main dependencies include: `Click` (for CLIs), `spacy` (for NLP), `deepl` (for translation), `genanki` (for Anki deck generation), `jinja2` (for templating, likely HTML output), `orjsonl` (for JSONL handling).
    *   Development dependencies include: `ruff`, `mypy`, `pytest`, `pytest-testmon`, `pytest-cov`, `pyfakefs`, `line_profiler`.
    *   Specifies Python version `==3.9`.
    *   Defines entry points for the command-line scripts: `book-to-flashcard`, `book-complexity`, `books-complexity`.
*   **`readme.md`**: Provides detailed user-facing documentation, including installation instructions and usage examples for the command-line tools.

## Key Technologies & Dependencies

*   Python 3.9
*   `uv` for package management and task running.
*   `spacy` for natural language processing (sentence splitting, grammatical analysis).
*   `DeepL API` for translation.
*   `Anki` (external application) for flashcard usage.
*   `Click` for creating command-line interfaces.
*   `genanki` for programmatically creating Anki decks.
*   `ruff` for linting.
*   `pytest` for testing.

## Getting Started

1.  **Installation**: Use `make install`
2.  **`spacy` language model**: Install the appropriate `spacy` model for the language of the books being processed (e.g., `fi_core_news_sm` for Finnish).
3.  **DeepL API Key**: A DeepL account and API key are needed for translation features.
4.  **Usage**: The tools are primarily command-line driven. Refer to `readme.md` for detailed examples.
5.  **Use the `Makefile`**: For common tasks like linting, testing, and building. The github build should always delegate everything to the Makefile. Developers should never need to remember manual command line steps to invoke tooling.
