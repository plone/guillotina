# Starting Guillotina

Once you have [guillotina installed](./installation.html), you can easily run it
with the `g` executable that it installs.


## Command

Then, simply run the default Guillotina command `g`.

```
g
```

Which should give you output like:

```
$ g
No configuration file found. Using default settings.
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

```eval_rst
.. note::
   Notice `No configuration file found. Using default settings.` This is because we have
   not created a configuration file. Default configuration is to use local file db.
```

The `g` executable allows you to potentially run a number of commands with Guillotina.
The default command is `serve` if none provided; however, you can explicitly run it with the
serve command name as well.

```
g serve
```

The serve command also takes `--host` and `--port` options to quickly change
without touching configuration.

In future sections, we'll explore other commands available.

## Check installation

Open up Postman or your favorite http client and do a basic `GET`
against `http://localhost:8080` with basic auth credentials for
`root` user and `root` password.

```bash
curl -X GET \
  http://localhost:8080 \
  -H 'Authorization: Basic cm9vdDpyb290' \
  -H 'Content-Type: application/json'
```

Also, do a `GET` on `http://localhost:8080/db`:

```bash
curl -X GET \
  http://localhost:8080 \
  -H 'Authorization: Basic cm9vdDpyb290' \
  -H 'Content-Type: application/json'
```

Finally, create a container in the db:

```bash
curl -X POST \
  http://localhost:8080/db \
  -H 'Authorization: Basic cm9vdDpyb290' \
  -H 'Content-Type: application/json' \
  -H 'Postman-Token: abd010be-138b-4780-8ce6-1e8175dd3c71' \
  -H 'cache-control: no-cache' \
  -d '{"@type": "Container", "id": "foobar"}'
```

Congratulations! You have Guillotina running!


## Useful run options

- `--reload`: auto reload on code changes. `requires aiohttp_autoreload`
- `--profile`: profile Guillotina while it's running
- `--profile-output`: where to save profiling output
- `--monitor`: run with aiomonitor. `requires aiomonitor`


**References**

  - [Quickstart](../../quickstart)
  - [Installation](../../installation/index)
  - [Configuraion](../../installation/configuration)
  - [Command Options](../../developer/commands)
