# Testing

## Customizing app settings on tests

You can use pytest markers to overwrite specific application settings
on tests, for instance:

```python
@pytest.mark.app_settings({
    'root_user__password': 'supersecret!'
})
async def my_test(container_requester):
    pass
```

Notice the use `__` to go down the nested configuration
structure.
