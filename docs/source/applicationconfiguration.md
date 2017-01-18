# Application Configuration

`plone.server` handles configuration application customizations and extension
mostly with decorators in code.

This page is meant to be a reference to the available decorators and options
to those decorators.


## service

*`configure.service`*

* _context_: Content type interface this service is registered against. Example: ISite
* _method_: HTTP method this service works against. Default is `GET`
* _permission_: Permission this service requires. Default is configure default_permission setting
* _layer_: Layer this service is registered for. Default is `IDefaultLayer`
* _name_: This is used as part of the uri. Example `@foobar` -> `/mycontent/@foobar`. Leave empty to be used for base uri of content -> `/mycontent`.


## content type

*`configure.contenttype`*

* _portal_type_: Name of the content type
* _schema_: Interface schema to use for type
* _add_permission_: Permission required to add content. Defaults to `plone.AddContent`
* _allowed_types_: List of types allowed to be added inside this content assuming it is a Folder type. Defaults to allowing all types.


## behavior

*`configure.behavior`*

* _title_: Name of behavior
* _provides_: Interface this behavior provides
* _marker_: Marker interface to apply to utilized instance's behavior
* _for__: Content type this behavior is available for


## addon

*`configure.addon`*

* _name_
* _title_
