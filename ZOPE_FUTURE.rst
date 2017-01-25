Throwing this out there...

Zope has connotations and cognitive overhead for people to think about.

Long term, we'd like to fork/simply all zope dependencies.

The component architecture, interfaces and security is amazing software; however,
for simplification and longterm success of project, we'd like to pull whatever we can out.


Package candidates:

- zope.component
- zope.configuration
- zope.interface
- zope.lifecycleevent
- zope.schema
- zope.event


Basically... anything where a user would be make imports for packages,
we want those imports to be part of THIS package.
