# D01 Link and Hygiene Report

Date: 2026-02-25

## Applied fixes
- Removed stray `production` text from:
  - `docs/source/installation/index.rst`
  - `docs/source/contrib/index.rst`
- Updated outdated Python setup references from `python3.7` to `python3` / `Python 3.10+` in:
  - `docs/source/quickstart.md`
  - `docs/source/quick-tour.md`
  - `docs/source/training/installation.md`
  - `docs/source/training/introduction.md`
  - `docs/source/training/asyncio.md`
  - `docs/source/training/index.rst`
  - `docs/source/developer/design.md`
  - `README.rst`
- Corrected docs URL protocol in `README.rst` to HTTPS for ReadTheDocs links.
- Fixed wording issue in `docs/source/index.md` (`An main` -> `A main`).

## Build validation
- Command used:
  - `python -m sphinx -E -a -b html docs/source docs/build/html`
- Result:
  - Build succeeded.
  - Existing baseline warnings remain in legacy REST/API docs and autodoc sections.
  - No warnings introduced from files modified in D01.
