from guillotina import configure


configure.permission("guillotina.OAuthManageClients", "Manage OAuth clients")
configure.permission("guillotina.OAuthAuthorize", "Authorize OAuth clients")
configure.permission("guillotina.OAuthUseToken", "Use OAuth token endpoint")

configure.grant(permission="guillotina.OAuthManageClients", role="guillotina.Manager")
configure.grant(permission="guillotina.OAuthManageClients", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.OAuthAuthorize", role="guillotina.Authenticated")
