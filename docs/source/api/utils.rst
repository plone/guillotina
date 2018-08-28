:mod:`guillotina.utils`
-----------------------

.. automodule:: guillotina.utils

  .. autofunction:: get_current_request
  .. autofunction:: get_content_path
  .. autofunction:: iter_parents
  .. autofunction:: navigate_to
  .. autofunction:: get_owners
  .. autofunction:: get_object_url
  .. autofunction:: get_object_by_oid
  .. autofunction:: get_behavior

  .. autofunction:: get_authenticated_user
  .. autofunction:: get_authenticated_user_id

  .. autofunction:: strings_differ
  .. autofunction:: get_random_string

  .. autofunction:: resolve_dotted_name
  .. autofunction:: get_caller_module
  .. autofunction:: resolve_module_path
  .. autofunction:: get_module_dotted_name
  .. autofunction:: get_dotted_name
  .. autofunction:: import_class
  .. autofunction:: resolve_path

  .. autofunction:: merge_dicts
  .. autofunction:: apply_coroutine
  .. autofunction:: lazy_apply
  .. autofunction:: safe_unidecode

  .. autoclass:: Navigator
    :members:


:mod:`guillotina.utils.execute`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: guillotina.utils.execute

  .. autofunction:: after_request
  .. autofunction:: after_request_failed
  .. autofunction:: after_commit
  .. autofunction:: before_commit
  .. autofunction:: in_pool
  .. autofunction:: in_queue
  .. autofunction:: in_queue_with_func

  .. autoclass:: ExecuteContext
     :members: after_request, after_request_failed, after_commit, before_commit
