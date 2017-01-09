from plone.server.migrate import migration


@migration('plone.server', to_version='1.0a9')
def migrate_layers(site):
    from plone.server.registry import ILayers

    registry = site['_registry']
    layers = registry.for_interface(ILayers).active_layers
    layers = layers - frozenset(['plone.server.api.layer.IDefaultLayer'])
    layers = layers | frozenset({'plone.server.interfaces.layer.IDefaultLayer'})
    registry.for_interface(ILayers).active_layers = layers
