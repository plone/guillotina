About
=====

As the Web evolves, so do the frameworks that we use to work with the Web.
Guillotina is part of that evolution, providing an asynchronous web server
with a rich, REST-ful API to build your web applications around.

It is designed for building JavaScript applications. It is an API framework, not
a typical template-based rendering framework like most web frameworks (Django/Pyramid/Plone).
What we mean by this is that Guillotina will not generate HTML out-of-the-box for you.
It is designed to be consumed by JavaScript applications that do the HTML rendering.

Features:
  - REST JSON API
  - Built-in authentication/authorization, built-in JWT support
  - Hierarchical data/url structure
  - Permissions/roles/groups
  - Fully customizable permission/roles/groups based on hierarchical data structure
  - Robust customizable component architecture and configuration syntax
  - Content types, dynamic behaviors
  - Built-in CORS support
  - JSON schema support
  - PostgreSQL and CockroachDB drivers
  - Blobs

Guillotina is built on the lessons learned from great technologies of the
open source projects Plone, Zope, Pyramid and Django.

Inspirations:
 - Plone/Zope's hierarchical data model
 - Pyramid's decorator-based auto-discovery application configuration syntax
 - Django's global application settings style syntax
 - Zope's component architecture for building robustly customizable applications
 - Plone/Zope's security model
 - JSON Schema


Lessons Learned (from said inspired frameworks):
 - Trade-offs for the sake of performance is okay
 - Too many complex dependencies causes difficulties in management and upgrades
 - It's okay to fork dependency packages


History lesson
--------------

In the beginning, there was `bobo`.

`bobo` was what Jim Fulton called his initial idea of mapping objects to web
urls. It's an old idea. A beautiful idea. The developers of Guillotina think
it's the best possible way to conceptualize most content-centric APIs and
organization of how your web applications think about data or their APIs.

Think about this simple example. Assuming you have the following dictionary::

    {
      "foo": {
        "bar": {}
      }
    }

The corresponding urls for a site based off this dictionary would be:
 - http://localhost:8080/
 - http://localhost:8080/foo
 - http://localhost:8080/foo/bar

And so on... It's a simple way to build APIs from data around a hierarchy (or tree).

Extrapolating this concept, Jim Fulton also built the ZODB package. This was a
complete database built on serializing Python objects using the pickle library. Then,
frameworks like Zope (and eventually Plone), used this database and the `bobo`
style of publishing objects to URLs to build a framework and CMS around.


Forked dependency packages
~~~~~~~~~~~~~~~~~~~~~~~~~~

Guillotina has eaten a few packages that would have otherwise been dependencies.

The reasons for forking are:
  - Required to support asyncio
  - Provide tighter fit for framework
  - Make installations less painful and error-prone
  - Groking framework is easier when there is one package to import from


Forks:
  - parts of the ZODB data model: we're on a relational storage model now
  - plone.behavior
  - zope.security
  - zope.schema
  - zope.component/zope.configuration
  - zope.dublincore
  - zope.i18n
  - zope.lifecycleevent
  - zope.location
  - zope.event


What it isn't
-------------

- Guillotina is not a replacement for Plone
- Guillotina is not a re-implementation of Plone
- Guillotina does not implement all the features and APIs of Plone

It could some day with the `guillotina_cms` package but replacement of Plone is
not the goal of Guillotina.
