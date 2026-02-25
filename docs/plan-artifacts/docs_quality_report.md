# Documentation Quality Report

Date: 2026-02-25
Branch: `docs/guillotina-docs-v2-batch-master`

## Scope
Final sweep after documentation IA, core concept content, LLM discovery assets,
and CI quality gates work.

## Validation results

### 1) LLM discovery asset generation
Command:
```bash
python docs/scripts/generate_llms_assets.py
```
Result:
- Generated successfully.
- Items: 21
- llms-full sections included: 12

### 2) llms asset quality checks
Command:
```bash
python docs/scripts/check_llms_assets.py
```
Result:
- Passed.
- `llms-full.txt` size: 12,379 bytes (budget: 2,097,152 bytes).
- Duplicate ratio: 0.0000 (threshold <= 0.35).

### 3) Retrieval benchmark coverage
Command:
```bash
python docs/scripts/check_retrieval_coverage.py --top-k 5 --min-coverage 0.90
```
Result:
- Passed.
- Hits: 11/12
- Coverage: 91.67% (target: >= 90%)

### 4) Sphinx HTML build
Command:
```bash
python -m sphinx -b html docs/source docs/build/html
```
Result:
- Passed.

### 5) External linkcheck
Command:
```bash
python -m sphinx -b linkcheck docs/source docs/build/linkcheck
```
Result:
- Passed.
- No broken links reported in `docs/build/linkcheck/output.txt`.

## Build root artifact check
Verified root output includes:
- `llms.txt`
- `llms-full.txt`
- `robots.txt`
- `sitemap.xml`

## Rollout readiness
Status: Ready for PR/review.

Residual notes:
- Linkcheck ignores include known legacy external URLs that are unavailable; this
  keeps CI focused on actionable regressions.
