# Static files

To pull this all together, we'll create our web application that uses the api
to provide a very simple chat experience.

Copy the following files into a new folder `static` in your application:

```eval_rst
- :download:`chat.js <./_static/chat.js>`.
- :download:`index.html <./_static/index.html>`.
- :download:`main.css <./_static/main.css>`.
```


## Configure

Then, we'll setup Guillotina to serve the folder.

Modify your `config.yaml` file to add:

```yaml
static:
  status: ./static
```

## JS Applications

You can also serve the static files in a way where it works with JavaScript
applications that need to be able to translate URLs from something other than root.

```yaml
jsapps:
  static: ./static
```

With this configuration any request to a url like `http://localhost:8080/static/foo/bar`
will serve files from `http://localhost:8080/static`.
