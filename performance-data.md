# get_current_request

Initial:

```
Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
   285                                           @profilable
   286                                           def get_current_request() -> IRequest:
   287                                               """
   288                                               Return the current request by heuristically looking it up from stack
   289                                               """
   290        16          245     15.3      7.3      frame = inspect.currentframe()
   291       102          418      4.1     12.5      while frame is not None:
   292       102          692      6.8     20.7          request = getattr(frame.f_locals.get('self'), 'request', None)
   293       102          435      4.3     13.0          if request is not None:
   294        16           66      4.1      2.0              return request
   295        86         1129     13.1     33.7          elif isinstance(frame.f_locals.get('request'), Request):
   296                                                       return frame.f_locals['request']
   297        86          364      4.2     10.9          frame = frame.f_back
   298                                               raise RequestNotFound(RequestNotFound.__doc__)
```

After using aiotask_context

```
Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
   286                                           @profilable
   287                                           def get_current_request() -> IRequest:
   288                                               """
   289                                               Return the current request by heuristically looking it up from stack
   290                                               """
   291        10            7      0.7      5.8      try:
   292        10           98      9.8     81.7          task_context = aiotask_context.get('request')
   293        10            8      0.8      6.7          if task_context is not None:
   294        10            7      0.7      5.8              return task_context
   295                                               except ValueError:
   296                                                   pass
   297                                           
   298                                               # fallback
   299                                               frame = inspect.currentframe()
   300                                               while frame is not None:
   301                                                   request = getattr(frame.f_locals.get('self'), 'request', None)
   302                                                   if request is not None:
   303                                                       return request
   304                                                   elif isinstance(frame.f_locals.get('request'), Request):
   305                                                       return frame.f_locals['request']
   306                                                   frame = frame.f_back
   307                                               raise RequestNotFound(RequestNotFound.__doc__)
```


# resolve_dotted_name

Slow enough where it doesn't make sense to call it all the time. Pre-convert these
where it is possible.
