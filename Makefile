VENV = .env
UNAME := $(shell uname) # what OS are we on?

ifneq (,$(findstring MSYS_NT-,$(UNAME))) # Windows
BIN = $(VENV)/Scripts
else # Linux presumably
BIN = $(VENV)/bin
endif

ifneq (,$(findstring NT-5.1,$(UNAME))) # Windows
VENV_TARGET = $(BIN)/activate.bat
else # Linux presumably
VENV_TARGET = $(BIN)/activate
endif

PYTHON = $(BIN)/python
PIP = $(BIN)/pip
PIP-COMPILE = $(BIN)/pip-compile

requirements.txt: pyproject.toml
	$(PIP-COMPILE) pyproject.toml

setup: requirements.txt $(VENV_TARGET)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install ruff
	$(PIP) install build
	$(BIN)/spacy download en_core_web_sm
	$(BIN)/spacy download ru_core_news_sm

setup-edit: setup
	$(PIP) install -e .

clean:
	rm -rf __pycache__
	rm -rf $(VENV)

lint: 
	$(BIN)/ruff check .
	
lint-github: 
	$(BIN)/ruff check . --output-format=github

.PHONY: test
test:
	$(PYTHON) -m unittest discover -s test

$(VENV_TARGET): requirements.txt
	python3 -m venv $(VENV)

.PHONY: dist
dist:
	$(PYTHON) -m build

all: $(VENV_TARGET) requirements.txt