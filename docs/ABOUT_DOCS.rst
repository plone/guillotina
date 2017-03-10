Meta Docs
=========

Our docs are built with sphinx.

In order to build the docs locally, you can run the buildout-docs.cfg buildout file.


We use a mix of RestructuredText and MarkDown in these docs because, well,
we're difficult I guess.

In any case, to build locally, do::

  cd docs
  make html -e SPHINXBUILD=../bin/sphinx-build
