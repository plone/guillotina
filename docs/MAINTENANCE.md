# Documentation Maintenance

## Ownership
- Primary maintainers: Guillotina core maintainers and active docs contributors.
- Review model:
  - docs changes should be reviewed alongside code changes that alter behavior.
  - concept/reference updates should include cross-link checks.

## Cadence
- Per PR: run docs build and CI docs job.
- Weekly: review failed linkcheck results and fix/update external references.
- Monthly: review LLM curation quality and prune noisy/low-value sections.
- Per release: verify migration docs and changelog links remain correct.

## Recurring checks
- `llms-full.txt` size remains under configured budget (2 MB).
- duplicate ratio in `llms-full.txt` stays under CI threshold.
- retrieval benchmark coverage remains at or above 90% target.
- no new broken internal links in docs build/link outputs.

## Regeneration workflow
```bash
python docs/scripts/generate_llms_assets.py
python docs/scripts/check_llms_assets.py
python docs/scripts/check_retrieval_coverage.py --top-k 5 --min-coverage 0.90
python -m sphinx -b html docs/source docs/build/html
python -m sphinx -b linkcheck docs/source docs/build/linkcheck
```

## When structure changes
- Update `docs/source/index.md` navigation first.
- Keep compatibility stubs/cross-links for moved high-traffic pages.
- Update `docs/source/_llm/curation.yml` and regenerate assets.
- Update benchmark queries if discovery paths changed significantly.

## Known external-link policy
Some legacy external links may become unavailable over time. Prefer:
1. replacing with canonical upstream links when possible,
2. documenting ignored links in `docs/source/conf.py` when unavoidable,
3. creating follow-up tasks to remove stale references.
