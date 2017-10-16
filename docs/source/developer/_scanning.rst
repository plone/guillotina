.. note:: **Scanning**

    If your service modules are not imported at run-time, you may need to provide an
    additional scan call to get your services noticed by `guillotina`.

    In your application `__init__.py` file, you can simply provide a `scan` call like::

        from guillotina import configure
        def includeme(root):
            configure.scan('my.package')
