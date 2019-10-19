# Starting Guillotina

Once you have [guillotina installed](./installation.html "Link to install docs"), you can run it
with the `g` executable that it installs.

## Command

Run the default Guillotina command `g`.

``` shell
g
```

Which should give you output like:

``` shell
$ g
No configuration file found. Using default settings with DUMMY_FILE db.
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

The `g` executable allows you to run a number of commands with Guillotina.

The default command is `serve` if none provided; nevertheless, you can explicitly run it with the
serve command name as well.

```
g serve
```

The serve command also takes `--host` and `--port` options to change without touching configuration.

In future sections, you'll explore other commands available.

## Check installation

Open up Postman and do a basic `GET` against `http://localhost:8080` with
basic auth credentials for `root` user and `root` password.

Also, do a `GET` on `http://localhost:8080/db`.

**Congratulations! You have Guillotina running!**


## Useful run options

- `--reload`: auto reload on code changes. `requires aiohttp_autoreload`
- `--profile`: profile Guillotina while it's running
- `--profile-output`: where to save profiling output
- `--monitor`: run with aiomonitor. `requires aiomonitor`


**References**

  - [Quickstart](../../quickstart)
  - [Installation](../../installation/index)
  - [Configuration](../../installation/configuration)
  - [Command Options](../../developer/commands)
