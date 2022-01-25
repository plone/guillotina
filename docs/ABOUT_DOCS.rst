Meta Docs
=========

Our docs are built with sphinx.

In order to build the docs locally, you need a sphinx running with the requirements
in the `docs-requirements.txt` file.


We use a mix of RestructuredText and MarkDown in these docs because, well,
we're difficult I guess.


.. code-block:: shell

  python3.7 -m venv .
  source bin/activate
  pip install guillotina
  pip install -r docs-requirements.txt
  cd docs
  make html