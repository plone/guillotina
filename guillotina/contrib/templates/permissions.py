from guillotina import configure


configure.permission("guillotina.AddJinjaTemplate", title="Add Jinja template")

configure.grant(permission="guillotina.AddJinjaTemplate", role="guillotina.Manager")
configure.grant(permission="guillotina.AddJinjaTemplate", role="guillotina.ContainerAdmin")
