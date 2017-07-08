# Application Configuration

`guillotina` handles configuration application customizations and extension
mostly with decorators in code.

This page is meant to be a reference to the available decorators and options
to those decorators.


## service

*`@configure.service`*

* _context_: Content type interface this service is registered against. Example: IContainer: *required*
* _method_: HTTP method this service works against. Default is `GET`
* _permission_: Permission this service requires. Default is configure default_permission setting
* _layer_: Layer this service is registered for. Default is `IDefaultLayer`
* _name_: This is used as part of the uri. Example `@foobar` -> `/mycontent/@foobar`. Leave empty to be used for base uri of content -> `/mycontent`.


## content type

*`@configure.contenttype`*

* _type_name_: Name of the content type: *required*
* _schema_: Interface schema to use for type: *required*
* _add_permission_: Permission required to add content. Defaults to `guillotina.AddContent`
* _allowed_types_: List of types allowed to be added inside this content assuming it is a Folder type. Defaults to allowing all types.


## behavior

*`@configure.behavior`*

* _title_: Name of behavior
* _provides_: Interface this behavior provides
* _marker_: Marker interface to apply to utilized instance's behavior
* _for__: Content type this behavior is available for


## addon

*`@configure.addon`*

* _name_: *required*
* _title_: *required*


## adapter

*`@configure.adapter`*

* _for__: Type or list of types this adapter adapts: *required*
* _provides_: Interface this adapter provides: required
* _name_: Your adapter can be named to be looked up by name
* _factory_: To use without decorator syntax, this allows you to register adapter of class defined elsewhere


## subscriber

*`@configure.subscriber`*

* _for__: Type or list of types this subscriber is for: *required*
* _handler_: A callable object that handles event, this allows you to register subscriber handler defined elsewhere
* _factory_: A factory used to create the subscriber instance
* _provides_: Interface this adapter provides--must be used along with factory


## utility

*`@configure.utility`*

* _provides_: Interface this utility provides
* _name_: Name of utility
* _factory_: A factory used to create the subscriber instance


## permission

*`configure.permission`*

* _id_
* _title_
* _description_


## role

*`configure.role`*

* _id_
* _title_
* _description_

## grant

*`configure.grant`*

* _role_: ID of role
* _principal_: ID of principal to grant to
* _permission_: ID of permission to grant
* _permissions_: List of permission IDs to grant to


## grant_all

*`configure.grant_all`*

* _principal_: ID of principal
* _role_: ID of role


# Overriding Configuration

`guillotina` applications can override default `guillotina` configuration.

If multiple `guillotina` applications configure conflicting configurations,
`guillotina` chooses the configuration according to the order the `guillotina`
applications that are included.
