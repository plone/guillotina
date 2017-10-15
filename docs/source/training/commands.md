# Commands

Guillotina comes with a great set of [commands](../../developer/commands.html) you
can use to help debug and inspect your install.

We've already gone through the `serve`, `create` and `testdata` commands so we'll
now cover `shell` and `run`.

Make sure to also read the [commands](../../developer/commands.html) reference in the docs
to learn how to create your own commands.

## Shell

The `shell` command allows you to get an interactive prompt into guillotina.

From here, you can connect to the database, accees objects and commit new data.


```
g -c config.yml shell
```

Then, to connect to the database and get your container object.

```python
txn = await use_db('db')
container = await use_container('container')
```

From here, you can access objects:

```python
conversations = await container.async_get('conversations')
await conversations.async_keys()
```


## Run

The `run` command allows you to run a python script directly.

```
g -c config.yaml run --script=path/to/script.py
```

In order for you to utilize this, the script must have an async function named
`run` inside it.


```python
async def run(container):
    pass
```
