About
=====

As the Web evolves, so do the frameworks that we use to work with the Web.
Guillotina is part of that evolution, providing an asynchronous web server
with a rich, REST-ful API to build your web applications around.

It is designed for building JavaScript applications. It is an API framework, not
a typical template-based rendering framework like most web frameworks (Django/Pyramid/Plone).
What we mean by this is that Guillotina will not generate HTML out-of-the-box for you.
It is designed to be consumed by JavaScript applications that do the HTML rendering,
or to act as a middleware layer on a microservice architecture.


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


An Object Graph: The guillotina datastore.
------------------------------------------

At the beginning there is the notion of Content-Type. A content type, it's just
a python interface (A class) that describes an object. Every object could be stored
on the db. And every object, could have child objects related to them. Something like:

/user@account/
/user@account/preferences
/user@account/todos
/user@account/todos/todos_list1
/user@account/todos/todos_list1/todo_item1
/user@account/todos/todos_list1/todo_item2
/user@account/todos/todos_list1/todo_item3

Allows us to better express content relations, and this is where guillotina shines, because
it offers an automatic REST API over them.

For example you can do a PATCH request over /user@account/preferences, to update, them or
you can POST an item over the /user@account/todos with the necessary payload to create new
todo posts lists, or you can just do a DELETE request
to /user@account/todos/todos_list1/todo_item3 to remove a todo list item.

That's the main foundation of guillotina, and also one of the most powerful concepts,
the permission system, is based on this. As an example, at /user@account path, only the user
is allowed to access it. All child objects inherit this permission, anyone else than the owner could
access them, but if at some point, we add new readers to an item (a todo list) will give access to
other users.

Security is accessed throught /object_path/@sharing




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

It could come some day with the `guillotina_cms` package but replacement of Plone is
not the goal of Guillotina.
