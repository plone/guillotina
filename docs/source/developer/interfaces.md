# Interfaces

`guillotina` uses interfaces to abstract and define various things including
content. Interfaces are useful when defining api contracts, using inheritance,
defining schema/behaviors and being able to define which content your services
are used for.

In the services example, you'll notice the use of `context=IContainer` for the service
decorator configuration. In that case, it's to tell `guillotina` that the
service is only defined for a container object.

## Common interfaces

Interfaces you will be interested in defining services for are:

 - `guillotina.interface.IDatabase`: A database contains the container objects
 - `guillotina.interface.IContainer`: Container content object
 - `guillotina.interface.IResource`: Base interface for all content
 - `guillotina.interface.IContainer`: Base interface for content that can contain other content
 - `guillotina.interface.IRegistry`: Registry object interface
 - `guillotina.interface.IDefaultLayer`: Layers are an interface applied to the
   request object. IDefaultLayer is the base default layer applied to the request object.
