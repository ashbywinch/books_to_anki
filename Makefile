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
PYTEST = $(BIN)/pytest
PIP = $(BIN)/pip
PIP-COMPILE = $(BIN)/pip-compile

$(PIP-COMPILE): $(VENV_TARGET)
	$(PIP) install pip-tools

requirements.txt: pyproject.toml $(PIP-COMPILE) 
	$(PIP-COMPILE) pyproject.toml

setup: requirements.txt $(VENV_TARGET) 
	$(PIP) install setuptools
	$(PIP) install -r requirements.txt
	$(PIP) install ruff
	$(PIP) install mypy
	$(PIP) install parameterized
	$(PIP) install line_profiler
	$(PIP) install pytest
	$(PIP) install pytest-cov
	$(PIP) install build
	$(PYTHON) -m spacy download en_core_web_sm
	$(PYTHON) -m spacy download ru_core_news_sm

install:
	$(PIP) install .

install-edit: 
	$(PIP) install -e .

clean:
	rm -f requirements.txt
	rm -rf __pycache__
	rm -rf $(VENV)

lint: 
	$(BIN)/ruff check .
	
lint-github: 
	$(BIN)/ruff check . --output-format=github

.PHONY: test
test:
	$(PYTEST)

profile:
	$(PYTHON) -m kernprof -lz .\test\call_book_complexity.py 
	mv call_book_complexity.py.lprof .\profiler
	$(PYTHON) -m line_profiler -rmt ".\profiler\call_book_complexity.py.lprof"

$(VENV_TARGET):
	python -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip

.PHONY: dist
dist:
	$(PYTHON) -m build
