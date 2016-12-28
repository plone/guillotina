from plone.server.migrate import migration


@migration('plone.server', to_version='1.0a9')
def migrate_stub(site):
    # just a stub so we write out migration data to registry
    pass
