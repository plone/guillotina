Meta Docs
=========

Our docs are built with sphinx.

In order to build the docs locally, you'll need sphinx + recommonmark installed.

Generally, that might looks something like this::

  pip install sphinx
  pip install recommonmark


We use a mix of RestructuredText and MarkDown in these docs because, well,
we're difficult I guess.

In any case, to build locally, do::

  make html
