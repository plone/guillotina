:mod:`guillotina.content`
-------------------------

.. automodule:: guillotina.content

  .. autoclass:: Resource
     :members: uuid, acl, add_behavior, remove_behavior
     :special-members: __name__, __parent__, __behaviors__

  .. autoclass:: Item

  .. autoclass:: Folder
     :members: async_contains, async_set, async_get, async_del, async_len, async_keys, async_items, async_multi_get

  .. autoclass:: Container
     :members: install

  .. autofunction:: create_content_in_container
  .. autofunction:: get_all_possible_schemas_for_type
  .. autofunction:: iter_schemata
  .. autofunction:: move
  .. autofunction:: duplicate