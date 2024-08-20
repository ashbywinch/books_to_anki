from book_complexity import get_books_complexity

# One-shot for generating a package from a big folder of books
# Useful for testing/profiling
# None of the test data is distributed.

if __name__ == "__main__":
    with open("data/vocabulary.csv", mode="rb") as vocabulary, open(
        "data/ru-freq.csv", mode="rb"
    ) as frequencycsv:
        get_books_complexity(
            inputfolder="data/books",
            pipeline="ru_core_news_sm",
            knownmorphs=vocabulary,
            frequencycsv=frequencycsv,
            outputfilename="complexity.jsonl",
        )
