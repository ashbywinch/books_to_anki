from pathlib import Path
from book_to_flashcards import cards_untranslated_from_folder
from book_to_flashcards import cards_to_jsonl
from book_to_flashcards.cards_untranslated_from_text import card_trim_title, cards_skip_first_line_if_author

# One-shot for generating a package from a big folder of books
# Useful for testing/profiling
# None of the test data is distributed.

if __name__ == "__main__":
    all_cards = cards_untranslated_from_folder(
        inputfolder="data/books",
        pipeline="ru_core_news_sm",
        maxfieldlen=120,
    )
    trimmed_cards = ( card_trim_title(card, "_") for card in all_cards )
    cards = cards_skip_first_line_if_author(trimmed_cards)
    outputfolder = Path("./test/output/")
    outputfolder.mkdir(exist_ok=True)
    cards_to_jsonl(
        cards,
        outputfileorfolder = outputfolder
    )
    #cards_to_anki(cards, ankifile=Path(outputfolder, "test.apkg"), fontsize=20, structure=True)