# Testing

## Customizing app settings on tests

You can use pytest markers to overwrite specific application settings
on tests, for instance:

```python
@pytest.mark.app_settings({
    'root_user: {'password': 'supersecret!'}
})
async def test_the_code(container_requester):
    pass
```

The above test would run a guillotina server with `supersecret!` root
password.
