Throwing this out there...

Zope has connotations and cognitive overhead for people to think about.

Long term, we'd like to fork/simply all zope dependencies.

The component architecture, interfaces and security is amazing software; however,
for simplification and longterm success of project, we'd like to pull whatever we can out.



Package removal/replacements...


difficult to remove
-------------------

- zope.annotation -> with db changes...
  - zope.schema
  - zope.proxy
- zope.configuration
  - zope.i18nmessageid
  - zope.interface
  - zope.schema
- zope.component
  - zope.event
  - zope.interface
- zope.event
- zope.i18n
  - zope.schema
  - zope.i18nmessageid
  - zope.component
  - pytz
