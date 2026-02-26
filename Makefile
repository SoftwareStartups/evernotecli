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
	uv run encl serve

thrift:
	rm -rf evernote_client/edam
	thrift --gen py:enum,type_hints -out . evernote_client/thrift/NoteStore.thrift | grep -vE "64-bit constant|No generator named|^$$" || true;
	thrift --gen py:enum,type_hints -out . evernote_client/thrift/UserStore.thrift | grep -vE "64-bit constant|No generator named|^$$" || true;
	thrift --gen py:enum,type_hints -out . evernote_client/thrift/Types.thrift | grep -vE "64-bit constant|No generator named|^$$" || true;
	thrift --gen py:enum,type_hints -out . evernote_client/thrift/Errors.thrift | grep -vE "64-bit constant|No generator named|^$$" || true;
	thrift --gen py:enum,type_hints -out . evernote_client/thrift/Limits.thrift | grep -vE "64-bit constant|No generator named|^$$" || true;
	rm -f evernote_client/edam/notestore/NoteStore-remote \
	      evernote_client/edam/userstore/UserStore-remote __init__.py

clean:
	rm -rf .venv .mypy_cache .ruff_cache .pytest_cache .coverage dist build *.egg-info
