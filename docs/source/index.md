# Guillotina: The Python AsyncIO REST API Framework

Guillotina is the only full-featured Python AsyncIO REST Resource Application
Server designed for high-performance, horizontally scaling solutions.


# Getting Started

Are you new to Guillotina? This is the place to start!

 - [Quick tour of Guillotina](./quick-tour.html) gives an overview of the major features in
   Guillotina, covering a little about a lot.
 - For help getting Guillotina set up, try
   [Installing Guillotina](./installation/installation.html).
 - Need help? Join our [Gitter channel](https://gitter.im/plone/guillotina).


# REST API

After you're up and running, primarily, Guillotina provides a REST API to work with
and it is what you should become the most familiar with.

Guillotina API structure mirrors the object tree structure. Within the object
tree structure, there are four major types of objects you'll want to be familiar
with:

- Application: The root of the tree: `/`
- Database: A configured database: `/(db)`
- Container: An main object to add data to: `/(db)/(container)`
- Content: Item or Folder by default. This is your dynamic object tree you create

The endpoints available around these objects are detailed below:

```eval_rst
.. toctree::
   :maxdepth: 1
   :glob:

   rest/application
   rest/db
   rest/container
   rest/item
   rest/folder
```

# Narrative Documentation

```eval_rst
.. toctree::
   :maxdepth: 2

   developer/narrative
   developer/security
   developer/roles
   developer/applications
   developer/addons
   developer/services
   developer/render
   developer/contenttypes
   developer/behavior
   developer/interfaces
   developer/commands
   developer/applicationconfiguration
   developer/design
   developer/persistence
   developer/blob
   developer/router
   developer/exceptions
   developer/fields
   developer/async_utils
```

# Programming API Reference

```eval_rst
.. toctree::
   :maxdepth: 1

   api/content
   api/request
   api/response
   api/fields
   api/utils
```


# Training

```eval_rst
.. toctree::
   :maxdepth: 1
   :glob:

   training/*
```

# About


```eval_rst
 .. toctree::
    :hidden:
    :glob:

    developer/*
    installation/*
    training/*
    *
```
