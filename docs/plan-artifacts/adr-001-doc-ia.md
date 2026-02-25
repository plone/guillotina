# ADR-001: Documentation IA Naming and Migration Strategy

- Status: Accepted
- Date: 2026-02-25
- Scope: Baseline decisions before IA refactor tasks

## Context
A baseline audit was required before changing documentation structure to avoid link
breakage and naming drift.

## Audit findings (stale assumptions checked against real files)
1. There is no existing `concepts/`, `how-to/`, or `operations/` directory in
   `docs/source/` yet.
2. The docs entrypoint currently mixes tutorial/reference/developer/deploy
   concerns in `docs/source/index.md`.
3. `docs/Makefile` expects `../bin/sphinx-build`; this path is absent in this
   workspace unless a local venv is manually created there.
4. Legacy pages (`quickstart`, `quick-tour`, `developer/*`, `installation/*`)
   are externally linkable and should remain stable during migration.

## Decisions
1. Canonical IA naming for this migration:
   - `getting-started/`
   - `how-to/`
   - `concepts/`
   - `reference/`
   - `operations/`
   - `contrib/`
   - `migration/`
2. Keep backward compatibility by using stubs/cross-links for moved high-traffic
   pages.
3. Prefer incremental content mapping over one-shot large moves.
4. Treat `contrib/` and `migration/` as stable top-level sections in this phase
   to reduce migration risk.

## Artifacts
- Inventory: `docs/plan-artifacts/docs_inventory.csv`
- Redirect map: `docs/plan-artifacts/redirect_map.csv`

## Gate result
- No unresolved naming/path conflicts identified for starting Phase 1 and Phase 2.
