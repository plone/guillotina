About The Documentation
=======================

This project documentation is organized to support both:

- human readers (contributors, operators, integrators), and
- machine-assisted workflows (LLM and crawler navigation).

Documentation model
-------------------

Primary structure is Diataxis-aligned:

- ``getting-started`` style content (quickstart, quick tour, training)
- ``how-to`` task-oriented guidance
- ``concepts`` explanatory and architecture pages
- ``reference`` API-oriented material
- ``operations`` deployment and migration guidance
- ``contrib`` optional integrations

Machine-readable layer
----------------------

Generated assets are published at docs root:

- ``llms.txt``
- ``llms-full.txt``
- ``robots.txt``
- ``sitemap.xml``

These files are generated from curated sources using:

- ``docs/scripts/generate_llms_assets.py``
- ``docs/source/_llm/curation.yml``

They are intended for generic crawlers and agents that follow the ``llms.txt``
convention. Context7 indexes ``docs/source/`` directly via ``context7.json`` at
the repository root and does not read the generated ``_extra/`` assets.

Contributor expectations
------------------------

When adding or updating docs:

1. Keep page titles and section headings stable and descriptive.
2. Add concise summaries for concept-heavy pages.
3. Prefer extending current pages before introducing duplicates.
4. Preserve link compatibility when moving content (stubs/cross-links).
5. Regenerate LLM/crawler assets when curated pages change.
6. Review docs changes alongside code changes that alter behavior.

When structure changes
----------------------

1. Update ``docs/source/index.md`` navigation first.
2. Keep compatibility stubs or cross-links for moved high-traffic pages.
3. Update ``docs/source/_llm/curation.yml`` and regenerate assets.
4. Commit regenerated files under ``docs/source/_extra/``.

External links
--------------

Some legacy external links may become unavailable over time. Prefer:

1. replacing with canonical upstream links when possible,
2. documenting ignored links in ``docs/source/conf.py`` when unavoidable,
3. creating follow-up tasks to remove stale references.

Quality checks
--------------

Run locally before opening a PR:

.. code-block:: shell

   python docs/scripts/generate_llms_assets.py
   python -m sphinx -b html docs/source docs/build/html
   python docs/scripts/check_llms_assets.py --html-root docs/build/html
   python -m sphinx -b linkcheck docs/source docs/build/linkcheck

CI enforces LLM asset checks (size, duplicate ratio, URL/HTML consistency) and
the Sphinx HTML build. Linkcheck runs in CI with ``continue-on-error`` for
legacy external URLs.
