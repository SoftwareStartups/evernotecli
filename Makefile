.PHONY: install lint format typecheck check test serve clean

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run pyright

check: lint typecheck

test:
	uv run pytest

serve:
	uv run mcp dev evernote_mcp/server.py

clean:
	rm -rf .venv .mypy_cache .ruff_cache .pytest_cache .coverage dist build *.egg-info
