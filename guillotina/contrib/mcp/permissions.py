from guillotina import configure


configure.permission("guillotina.MCPView", "View MCP integration services")
configure.permission("guillotina.MCPExecute", "Execute MCP tools")

configure.grant(permission="guillotina.MCPView", role="guillotina.Manager")
configure.grant(permission="guillotina.MCPView", role="guillotina.Owner")
configure.grant(permission="guillotina.MCPExecute", role="guillotina.Manager")
configure.grant(permission="guillotina.MCPExecute", role="guillotina.Owner")
configure.grant(permission="guillotina.MCPExecute", role="guillotina.Editor")
