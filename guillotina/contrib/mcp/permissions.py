from guillotina import configure


configure.permission("guillotina.mcp.Use", "Use MCP tools to query content")
configure.grant(permission="guillotina.mcp.Use", role="guillotina.Authenticated")
configure.permission("guillotina.mcp.IssueToken", "Issue a long-lived MCP token")
configure.grant(permission="guillotina.mcp.IssueToken", role="guillotina.Authenticated")
