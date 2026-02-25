# ADR-002: LLM Discovery and Crawl Policy

- Status: Accepted
- Date: 2026-02-25
- Related plan: `DOCUMENTATION_IMPROVEMENT_PLAN_LLM_READY.md` (section 8 decisions)

## Context
The documentation improvement plan requires explicit decisions before implementing
`llms.txt`, `llms-full.txt`, robots directives, and sitemap/canonical metadata.

## Decision 1: Canonical production docs URL base
- Canonical base URL: `https://guillotina.readthedocs.io/en/latest/`
- Rationale:
  - Existing references already point to ReadTheDocs.
  - The repository has an active `.readthedocs.yml` configuration.
  - `latest` is the stable, version-agnostic entrypoint for most users and agents.

## Decision 2: Bot access policy by environment
- Public production docs:
  - Allow standard crawling for documentation pages.
  - Keep explicit user-agent blocks available for rapid policy tightening if needed.
- Non-production/preview/private docs:
  - Default policy: disallow all crawling (`User-agent: *`, `Disallow: /`).
- Rationale:
  - Public docs should remain discoverable.
  - Non-production/private content should not be indexed or harvested.

## Decision 3: `llms-full.txt` size threshold
- Initial maximum size: `2 MB`.
- Rationale:
  - Keeps context payload bounded for retrieval and prompt usage.
  - Reduces duplication/noise risk.

## Decision 4: Changelog and migration inclusion in curation
- `llms.txt`:
  - Include links to changelog and migration landing pages.
- `llms-full.txt`:
  - Exclude changelog and migration body content by default.
  - Include only if a future policy change explicitly opts in.
- Rationale:
  - Preserve discovery of historical docs while keeping long-form corpus focused.

## Operational notes
- If project maintainers choose a different canonical host/version policy,
  update this ADR and regenerate LLM assets in the same change set.
- CI checks should enforce the `2 MB` cap and detect large duplicate ratios.
