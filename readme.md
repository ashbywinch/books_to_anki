# Tools for learning languages from books

Reading books and short stories is a great tool for language learning, and many languages
have lots of public domain books available for free download.
However, it can be difficult to find books at an appropriate level, and frustrating to read a book
as a language learner if your state of flow is constantly interrupted by having to look up words.

This package contains
1. book_to_flashcards, a tool to turn a book into a set of flashcards suitable for importing into Anki (https://apps.ankiweb.net/). Reading a book via flashcards can massively improve "flow" for language learners.

## Installation
Install python from here https://www.python.org/downloads/ if you don't already have it.
From a command line, run
```
> python3 -m pip install book_language_tools 
```
Use the instructions at the top of the page here https://spacy.io/usage/ to configure and install the model for the **language your books are written in**. Make a note of the name of the model.

## book_to_flashcards
This is a command line tool (and also a python package) that can take a large text file, split it into chunks suitable for displaying on flash cards, translate each chunk into a desired language, and output the resulting flash cards as a file, in CSV format, suitable for importing into Anki.

It uses AI language parsing (via the spacy library) to try and split long sentences into smaller chunks that can be individually understood and translated for use on a single flash card.

It uses DeepL to translate each card to a language of the user's choice.

The output file has one row per flash card.

###CSV fields
1. The index of the card. When Anki batch imports cards, it uses the first field on the card to detect whether a card is new or a duplicate.
2. A previous chunk of text, that can be used on the card to give context.
3. The main chunk of text to be displayed on the front of the flash card. This will be a snippet from the source text.
4. A following chunk of text that can be displayed for context.
5. A translation of the main chunk of text into the target language.
