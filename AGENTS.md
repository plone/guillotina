# AGENTS.md

## Project Overview
<<<<<<< docs/guillotina-docs-v2-batch-master

- Purpose: Guillotina async REST API/resource database project.
- Main stack: Python package with Sphinx documentation, pytest tests, and setuptools packaging.
- Key entrypoints: `guillotina.commands:command_runner`, console scripts `guillotina` and `g`.

## Development Commands

- Install dev environment: follow `README.rst` with a virtualenv, requirements, contrib requirements, and editable install with test extras.
- Docs linkcheck used in this workspace: `.venv/bin/python -m sphinx -b linkcheck docs/source docs/build/linkcheck`.
- Syntax smoke for Sphinx config: `python -m compileall -q docs/source/conf.py`.
- Tests from repo docs: `./bin/pytest guillotina`.

## Validation

- For docs-only changes, run Sphinx linkcheck when dependencies are available.
- Linkcheck currently includes known unrelated failures for localhost example URLs and may be affected by external DNS availability.

## Deployment Notes

- Iskra workspace policy applies: do not deploy this repo unless deployment is explicitly requested.
- Record the working branch in Ops Tracker closeout evidence.

## Constraints / Gotchas

- Iskra repos require a dedicated task branch; do not commit directly to `main` or `master`.
- Keep untracked virtualenvs and local generated artifacts out of commits.
- Do not commit secrets, local credentials, or kubeconfig material.

## Task Closeout Notes

- Record commit, branch, validation, and no-deploy status in Ops Tracker.
- Update `CHANGELOG.rst` for task outcomes when closing tracked work.
=======
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
  - `pip install -e '.[test]'`
- Run local server:
  - `g` (uses `config.yaml` by default)
- Run tests:
  - `.venv/bin/pytest guillotina/tests`
  - Targeted: `.venv/bin/pytest guillotina/tests/<path>`

## Validation
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
- Record branch name, commit hash, validation output, and task evidence in Ops Tracker.

>>>>>>> master
