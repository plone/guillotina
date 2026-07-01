# AGENTS.md

## Project Overview

- Purpose: Guillotina core framework and official contrib addons.
- Main stack: Python async API server (ASGI), PostgreSQL, optional Redis.
- Key paths:
  - `guillotina/` core framework and contrib packages
  - `guillotina/tests/` test suite
  - `docs/source/` documentation

## Development Commands

- Setup (local venv expected at repo root):
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
  - `pip install -r requirements.txt`
  - `pip install -r contrib-requirements.txt`
  - `pip install -e '.[test]' -e '.[testdata]'`
- Run local server:
  - `g` (uses `config.yaml` by default)
- Run tests:
  - `.venv/bin/pytest guillotina/tests`
  - Targeted: `.venv/bin/pytest guillotina/tests/<path>`

## Validation

- For docs-only changes, run:
  - `.venv/bin/python docs/scripts/generate_llms_assets.py`
  - `.venv/bin/python -m sphinx -b html docs/source docs/build/html`
  - `.venv/bin/python docs/scripts/check_llms_assets.py --html-root docs/build/html`
  - `.venv/bin/python docs/scripts/check_retrieval_coverage.py --top-k 5 --min-coverage 0.90`
  - `.venv/bin/python -m sphinx -b linkcheck docs/source docs/build/linkcheck`
- For contrib changes, run focused tests under the touched contrib test folder.
- For API/service changes, verify status codes and response payload contracts.
- Keep docs updated under `docs/source/contrib/` when adding contrib features.

## Deployment Notes

- This repo is a framework/library; no direct client deployment from this repo by default.
- Build/release lifecycle should follow package versioning (`VERSION`, `CHANGELOG.rst`).

## Constraints / Gotchas

- Keep compatibility with repository formatting (`black` line length 110).
- Avoid wrapper layers when task explicitly requires low-level protocol primitives.
- Never commit credentials or local environment files.

## Task Closeout Notes

- Update `CHANGELOG.rst` for notable changes.
- Record branch name, validation output, and task evidence when handing off work.
