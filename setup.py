from setuptools import setup, find_packages

setup(
    name='book-language-tools',
    version='0.1.0',
    py_modules=['book_to_flashcards'],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'spacy',
        'deepl',
        'unicodecsv',
    ],
    entry_points={
        'console_scripts': [
            'make-flashcards = book_to_flashcards:make_flashcard_csv',
        ],
    },
)