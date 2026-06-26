.PHONY: install test run clean

install:
	uv pip install -e .[dev]

test:
	uv run pytest

run:
	uv run python -m gonogo.cli

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
