Throwing this out there...

Zope has connotations and cognitive overhead for people to think about.

Long term, we'd like to fork/simply all zope dependencies.

The component architecture, interfaces and security is amazing software; however,
for simplification and longterm success of project, we'd like to pull whatever we can out.



Package removal/replacements...


difficult to remove
-------------------

- zope.proxy
- zope.configuration
- zope.component
- zope.event(z.component depends on)
- ZODB
- zope.schema
- zope.annotation -> with db changes...
- zodbpickle
- ZConfig
- zc.lockfile
- transaction
- BTrees
- persistent


?
-
- zope.i18nmessageid
- zope.i18n
