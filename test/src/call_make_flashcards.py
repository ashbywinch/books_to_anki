from pathlib import Path
from book_to_flashcards import cards_untranslated_from_folder
from book_to_flashcards import cards_to_jsonl

# One-shot for generating a package from a big folder of books
# Useful for testing/profiling
# None of the test data is distributed.

if __name__ == "__main__":
    cards = cards_untranslated_from_folder(
        inputfolder="data/books",
        pipeline="ru_core_news_sm",
        maxfieldlen=120
    )
    outputfolder = Path("./test/output/")
    outputfolder.mkdir(exist_ok=True)
    cards_to_jsonl(
        cards,
        outputfileorfolder = outputfolder
    )