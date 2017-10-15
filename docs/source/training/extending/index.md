# Extending

In our training, we'll be working on creating a simple chat application.

To extend Guillotina, we need to write a Python package.

Let's start by using the cookiecutter to bootstrap an application for us.


```
g create --template=application
```

Follow the prompts and name your application `guillotina_chat`.

Then,

```
cd guillotina_chat
python setup.py develop
```


```eval_rst
.. toctree::
   :maxdepth: 1

   configuration
   contenttypes
   install
   permissions
   events
   users
   serialize
   services
   utilities
   websockets
   static
```
