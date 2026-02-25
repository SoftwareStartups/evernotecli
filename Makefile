.PHONY: install lint format typecheck check test serve clean thrift

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

thrift:
	rm -rf evernote_mcp/edam
	thrift --gen py -out . evernote_mcp/thrift/NoteStore.thrift
	thrift --gen py -out . evernote_mcp/thrift/UserStore.thrift
	thrift --gen py -out . evernote_mcp/thrift/Types.thrift
	thrift --gen py -out . evernote_mcp/thrift/Errors.thrift
	thrift --gen py -out . evernote_mcp/thrift/Limits.thrift
	rm -f evernote_mcp/edam/notestore/NoteStore-remote evernote_mcp/edam/userstore/UserStore-remote __init__.py

clean:
	rm -rf .venv .mypy_cache .ruff_cache .pytest_cache .coverage dist build *.egg-info
