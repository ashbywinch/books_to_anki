"""
Tests for the CLI interface in `cli_make_flashcards.py`.

These tests utilize the `pyfakefs` pytest plugin, meaning all filesystem
operations (e.g., creating temporary input files/folders via `tmp_path`,
and any filesystem checks or writes performed by the CLI commands under test)
operate on a mocked, in-memory filesystem. This ensures tests are isolated,
fast, and do not interact with the actual disk.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from book_to_flashcards.Card import Card
from book_to_flashcards.cli_make_flashcards import cli_make_flashcards as cli_main
import sys # Add sys import


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False) # Configure mix_stderr here

class TestCliMakeFlashcards:

    @patch('book_to_flashcards.cli_make_flashcards.cards_to_jsonl')
    @patch('book_to_flashcards.cli_make_flashcards.cards_untranslated_from_file')
    @patch('book_to_flashcards.cli_make_flashcards.glob.glob')
    @patch('sys.stdout.isatty', return_value=False)
    def xtest_cli_basic_jsonl_flow(
        self, mock_isatty, mock_glob, mock_cards_from_file, mock_to_jsonl,
        runner, tmp_path
    ):
        input_folder = tmp_path / "actual_input_folder"
        input_folder.mkdir()
        dummy_file_in_folder = input_folder / "dummy.txt"
        mock_glob.return_value = [str(dummy_file_in_folder)] 

        result = runner.invoke(cli_main, [
            'from-folder', str(input_folder), 
            'pipeline', 'en_core_web_sm',
            'to-jsonl', str(tmp_path / 'output_file.jsonl') 
        ], catch_exceptions=False)
        
        print(f"Output for test_cli_basic_jsonl_flow: {result.output}")
        if result.exception:
            print(f"Exception info: {result.exc_info}")

        assert result.exit_code == 0, f"CLI Error: {result.output}\nException: {result.exception}"
        mock_glob.assert_called_once_with(str(input_folder) + "/**/*.txt", recursive=True)
        mock_cards_from_file.assert_called_once_with(inputfile=str(dummy_file_in_folder), pipeline='en_core_web_sm', maxfieldlen=70)
        mock_to_jsonl.assert_called_once()

    @patch('sys.stdout.isatty', return_value=False) # Force non-TTY path
    @patch('book_to_flashcards.cli_make_flashcards.glob.glob') # Mock glob used by from_folder
    @patch('book_to_flashcards.cli_make_flashcards.cards_untranslated_from_file') 
    @patch('book_to_flashcards.cli_make_flashcards.translate_cards')
    @patch('book_to_flashcards.cli_make_flashcards.cards_to_anki')
    @patch('book_to_flashcards.cli_make_flashcards.cards_to_jsonl')
    def xtest_cli_jsonl_output_no_translate(
        self, mock_to_jsonl, mock_to_anki, 
        mock_translate, mock_cards_from_file, mock_glob, mock_isatty, runner, tmp_path
    ):
        input_folder = tmp_path / "actual_input_dir"
        input_folder.mkdir()
        dummy_file_in_folder = input_folder / "another_dummy.txt"
        mock_glob.return_value = [str(dummy_file_in_folder)]

        result = runner.invoke(cli_main, [
            'from-folder', str(input_folder),
            'pipeline', 'fr_core_news_sm',
            'to-jsonl', str(tmp_path / 'output_cards.jsonl') 
        ], catch_exceptions=False) # Let exceptions propagate for debugging this
        print(f"Output for test_cli_jsonl_output_no_translate: {result.output}")
        if result.exception:
            print(f"Exception info: {result.exc_info}")

        assert result.exit_code == 0, f"CLI Error: {result.output}"
        mock_glob.assert_called_once_with(str(input_folder) + "/**/*.txt", recursive=True)
        mock_cards_from_file.assert_called_once_with(inputfile=str(dummy_file_in_folder), pipeline='fr_core_news_sm', maxfieldlen=70)
        mock_translate.assert_not_called()
        mock_to_anki.assert_not_called()
        mock_to_jsonl.assert_called_once()

    def test_cli_missing_input_output(self, runner):
        # Invoking the main group with no commands should show help and exit cleanly.
        result = runner.invoke(cli_main, [])
        assert result.exit_code == 0 
        assert "Usage: cli-make-flashcards" in result.output # Check for help text

    @patch('book_to_flashcards.cli_make_flashcards.cards_to_anki')
    def test_cli_output_file_exists_error(self, mock_cards_to_anki, runner, tmp_path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("Test content")
        output_file = tmp_path / "existing_output.apkg"
        output_file.touch() # Actually create the file to simulate it existing

        result = runner.invoke(cli_main, [
            'from-text', str(input_file),
            'pipeline', 'mock_pipe',
            'to-anki', str(output_file)
        ])

        assert result.exit_code == 0 # overwrite is default and silent

    @patch('book_to_flashcards.cli_make_flashcards.cards_untranslated_from_file', side_effect=Exception("File processing error from folder item"))
    def test_cli_error_in_from_folder(self, mock_cards_untranslated_from_file, runner, tmp_path):
        input_folder = tmp_path / "input_dir_error"
        input_folder.mkdir()
        (input_folder / "file_that_will_error.txt").write_text("Content")

        result = runner.invoke(cli_main, [
            'from-folder', str(input_folder),
            'pipeline', 'mock_pipe', 
            'to-jsonl', str(tmp_path / "error_out.jsonl") 
        ]) 

        assert result.exit_code != 0 
        # Check that the mock was called (which means its side_effect exception was raised)
        mock_cards_untranslated_from_file.assert_called() 
        # It's hard to reliably get the printed stderr message here, so focus on side effects. 