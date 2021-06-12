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

Modify your `__init__.py` file to add:

```python
app_settings = {
    "static": {
        "static": "guillotina:static"
    }
}
```

## JS Applications

You can also serve the static files in a way where it works with JavaScript
applications that need to be able to translate URLs from something other than root.

```python
app_settings = {
    "jsapps": {
        "static": "guillotina:static"
    }
}
```

With this configuration any request to a url like `http://localhost:8080/static/foo/bar`
will serve files from `http://localhost:8080/static`.
