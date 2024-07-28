from book_complexity import get_books_complexity

# One-shot for generating a package from a big folder of books
# Useful for testing/profiling
# None of the test data is distributed.

if __name__ == "__main__":
    with open("data/vocabulary.csv", mode="rb") as vocabulary, open(
        "data/ru-freq.csv", mode="rb"
    ) as frequencycsv, open("test/output/output.csv", mode="wb") as outputcsv:
        get_books_complexity(
            inputfolder="data/books-small",
            pipeline="ru_core_news_sm",
            outputcsv=outputcsv,
            knownmorphs=vocabulary,
            frequencycsv=frequencycsv,
        )
