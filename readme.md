# Tools for learning languages from books

Reading books and short stories is a great tool for language learning, and many languages
have lots of public domain books available for free download.
However, it can be difficult to find books at an appropriate level, and frustrating to read a book
as a language learner if your state of flow is constantly interrupted by having to look up words.

This package contains

1. books-to-anki, a tool to turn a book into a set of flashcards suitable for importing into Anki (<https://apps.ankiweb.net/>). Reading a book via flashcards can massively improve "flow" for language learners.
2. books-complexity, a tool to calculate various complexity metrics on text files. If you have a large corpus of texts, this can be used to identify suitable foreign language texts to study.

## Installation

Install python from here <https://www.python.org/downloads/> if you don't already have it.
From a command line, run

```python
> python3 -m pip install book_language_tools 
```

Use the instructions at the top of the page here <https://spacy.io/usage/> to configure and install the model for the **language your books are written in**. Make a note of the name of the model.

## books-to-flashcards

This is a command line tool (and also a python package) that can take a folder full of text files, and generate an anki package. The package will contain one anki deck per text file, and each deck will contain the entire text in order, split into flash-card-sized chunks, with the original text on the front of the card and the translated text on the back of the card.  

It uses AI language parsing (via the spacy library) to try and split long sentences in such a way that they can be individually understood and translated without context (although the previous and next chunks of text are displayed on the front of the card)

DeepL is used to translate each card to a language of the user's choice.

The length of the "text chunks" and the size of the font on the cards is configurable.

Use the following commandline for usage details:

```Powershell
books-to-flashcards --help
```

## books-complexity and book-complexity

These are command line tools (and also a python package "book_complexity") to calculate various complexity metrics for texts.

The metrics included are

* Word count
* Sentence count
* Words per sentence
* Mean word length
* Mean grammar depth
    This is calculated by making a grammatical tree from each sentence, and calculating the depth of that tree. So for example, a sentence using a lot of nested parentheses might have a very large depth, whereas the sentence "Jane eats apples" has a depth of 2.
* Words known
    This can be calculated if you provide a list of all the words you already know. If you've been using Anki for language learning, the extension "AnkiMorphs" can provide you with a list of words that are considered mature by Anki.
* Percent words known
* Vocabulary Level
    This is calculated if you supply a word frequency list for the language of the text. Frequency files for several languages can be found at <https://mortii.github.io/anki-morphs/user_guide/setup/prioritizing.html?highlight=frequency#custom-frequency-files>
    It divides the frequency list into subsets roughly corresponding to the CEFR levels:

    0. A1
    1. A2
    2. B1
    3. B2
    4. C1
    5. C2
    
    Currently it returns the maximum "level" of all the words in the text, although working from the 90% percentile would be a great improvement (watch this space!). It ignores words that are not in the frequency list.

```Powershell
book-complexity --help
books-complexity --help
```

