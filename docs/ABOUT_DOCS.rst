About The Documentation
=======================

This project documentation is organized to support both:

- human readers (contributors, operators, integrators), and
- machine-assisted workflows (retrieval and LLM navigation).

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

Contributor expectations
------------------------

When adding/updating docs:

1. Keep page titles and section headings stable and descriptive.
2. Add concise summaries for concept-heavy pages.
3. Prefer extending current pages before introducing duplicates.
4. Preserve link compatibility when moving content (stubs/cross-links).
5. Regenerate LLM/crawler assets when curated pages change.

Quality checks
--------------

Run locally before opening a PR:

.. code-block:: shell

   python docs/scripts/generate_llms_assets.py
   python docs/scripts/check_llms_assets.py
   python docs/scripts/check_retrieval_coverage.py --top-k 5 --min-coverage 0.90
   python -m sphinx -b html docs/source docs/build/html
   python -m sphinx -b linkcheck docs/source docs/build/linkcheck
