# AGENTS.md

## Project Overview

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
