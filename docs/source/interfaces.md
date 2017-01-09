# Interfaces

`plone.server` uses interfaces to abstract and define various things including
content. Interfaces are useful when defining api contracts, using inheritance,
defining schema/behaviors and being able to define which content your services
are used for.

In the services example, you'll notice the use of `context=ISite` for the service
decorator configuration. In that case, it's to tell `plone.server` that the
service is only defined for a site object.

## Common interfaces

Interfaces you will be interested in defining services for are:

 - `plone.server.interface.IDatabase`: A database contains the site objects
 - `plone.server.interface.ISite`: Site content object
 - `plone.server.interface.IResource`: Base interface for all content
 - `plone.server.interface.IContainer`: Base interface for content that can contain other content
 - `plone.server.interface.IRegistry`: Registry object interface
 - `plone.server.interface.IDefaultLayer`: Layers are an interface applied to the
   request object. IDefaultLayer is the base default layer applied to the request object.
