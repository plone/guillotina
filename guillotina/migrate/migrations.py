from guillotina.migrate import migration


@migration('guillotina', to_version='1.0a9')
def migrate_layers(site):
    from guillotina.registry import ILayers

    registry = site['_registry']
    layers = registry.for_interface(ILayers).active_layers
    layers = layers - frozenset(['guillotina.api.layer.IDefaultLayer'])
    layers = layers | frozenset({'guillotina.interfaces.layer.IDefaultLayer'})
    registry.for_interface(ILayers).active_layers = layers
