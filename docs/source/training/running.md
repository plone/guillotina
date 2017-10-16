# Starting Guillotina

Once you have [guillotina installed](./installation.html), you can easily run it
with the `g` executable that it installs.

However, before we begin, we'll need to run a postgresql server for Guillotina
to use.

```
docker run -e POSTGRES_DB=guillotina -e POSTGRES_USER=guillotina -p 127.0.0.1:5432:5432 postgres:9.6
```

```eval_rst
.. note::
   This particular docker run command produces a volatile database. Stopping and
   starting it again will cause you to lose any data you pushed into it.
```


## Command

Then, simply run the default Guillotina command `g`.

```
g
```

Which should give you output like:

```
$ g
Could not find the configuration file config.yaml. Using default settings.
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
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

Open up Postman and do a basic `GET` against `http://localhost:8080` with
basic auth credentials for `root` user and `root` password.

Also, do a `GET` on `http://localhost:8080/db`.

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
