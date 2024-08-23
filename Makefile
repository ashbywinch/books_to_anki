UNAME := $(shell uname) # what OS are we on?

uv:
ifneq (,$(findstring NT-5.1,$(UNAME))) # Windows
	powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
else # Linux presumably
	curl -LsSf https://astral.sh/uv/install.sh | sh
endif

setup: uv
	uv sync

install:
	uv pip install .

install-edit: 
	uv pip install -e .

clean:
	rm -rf __pycache__
	rm -rf .venv

lint: 
	uv run ruff check .
	
lint-github: 
	uv run ruff check . --output-format=github

.PHONY: test
test: 
	uv run pytest --cov=src --cov-report=xml --no-testmon

testprofile:
	uvx hyperfine "make test" --export-asciidoc test_timing.txt -i
	
profile:
	uv run kernprof -lz .\test\src\call_book_complexity.py 
	mv call_book_complexity.py.lprof .\profiler
	python -m line_profiler -rmt ".\profiler\call_book_complexity.py.lprof"

.PHONY: dist
dist:
	uv run pyproject-build
