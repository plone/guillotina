# Using the Guillotina API

Before we start using the Guillotina API, let's get us some test data to play with.

Using the `testdata` command, we'll populate our database with some data from
wikipedia.


```
g testdata --per-node=5 --depth=2 --container=container
```


## Interacting with the API

You can use whatever you'd like but this training will mention use of Postman.

Open up Postman and do a `GET` on `http://localhost:8080/db/container`
with the username `root` and password `root` for basic auth.

We can not necessarily go over every single API but will touch on a few and
give a general understanding of how to explore and use the API.


## Creating content

To create content, do a `POST` request on a container or folder object.

```eval_rst
.. http:gapi::
   :hidden:
   :path: /db/container
   :basic_auth: root:root
   :method: POST
   :body: {
          "@type": "Container",
          "id": "container"
        }

.. http:gapi::
   :path: /db/container
   :path_spec: /(db)/(container)
   :basic_auth: root:root
   :method: POST
   :body: {
          "@type": "Item",
          "id": "foobar5"
        }
```


## Adding behaviors

To add a dynamic behavior, we use the `@behavior` endpoint.

```eval_rst
.. http:gapi::
   :path: /db/container/foobar5/@behaviors
   :path_spec: /(db)/(container)/(content)/@behaviors
   :method: PATCH
   :basic_auth: root:root
   :body: {
          "behavior": "guillotina.behaviors.attachment.IAttachment"
        }
```


## Uploading files

Simple file uploads can be done with the `@upload` endpoint.

```eval_rst
.. http:gapi::
   :path: /db/container/foobar5/@upload/file
   :path_spec: /(db)/(container)/(content)/@upload/file
   :method: PATCH
   :basic_auth: root:root
   :body: <text data>
```

Then, to download the file, use the `@download` endpoint.

```eval_rst
.. http:gapi::
   :path: /db/container/foobar5/@download/file
   :path_spec: /(db)/(container)/(content)/@download/file
   :basic_auth: root:root
   :body: <text data>
```

## Uploading files with TUS

Guillotina also supports the TUS protocol using the `@tusupload` endpoint. The
TUS protocol allows you to upload large files in chunks and allows you to have
resumable uploads.


First, initialize the TUS upload with a POST

```eval_rst
.. http:gapi::
   :path: /db/container/foobar5/@tusupload/file
   :path_spec: /(db)/(container)/(content)/@tusupload/file
   :method: POST
   :headers: TUS-RESUMABLE:1,UPLOAD-LENGTH:22
   :basic_auth: root:root
```

Next, upload the chunks(here we're doing chunks):

```eval_rst
.. http:gapi::
   :path: /db/container/foobar5/@tusupload/file
   :path_spec: /(db)/(container)/(content)/@tusupload/file
   :method: PATCH
   :headers: TUS-RESUMABLE:1,Upload-Offset:0
   :basic_auth: root:root
   :body: <text data>
```

And final chunk:

```eval_rst
.. http:gapi::
   :path: /db/container/foobar5/@tusupload/file
   :path_spec: /(db)/(container)/(content)/@tusupload/file
   :method: PATCH
   :headers: TUS-RESUMABLE:1,Upload-Offset:11
   :basic_auth: root:root
   :body: <text data>
```

### Unknown upload size

Guillotina's TUS implementation has support for the `Upload-Defer-Length` header.
This means you can upload files with an unknown final upload size.

In order to implement this correctly, you will need to provide the
`Upload-Defer-Length: 1` header and value on the initial POST to start the TUS
upload. You are then not required to provide the `UPLOAD-LENGTH` header.

Then, before or on your last chunk, provide a `UPLOAD-LENGTH` value to let
TUS know the upload can not finish.


### Simultaneous TUS uploads

Guillotina's TUS implementation also attempts to prevent simultaneous uploaders.

If two users attempt to start an upload on the same object + field at the same
time, a 412 error will be thrown. Guillotina tracks upload activity to detect this.
If there is no activity detected for 15 seconds with an unfinished TUS upload,
no error is thrown.

To override this, send the `TUS-OVERRIDE-UPLOAD: 1` header.


## Modifying permissions

The `@sharing` endpoint is available to inspect and modify permissions on an object.

```eval_rst
.. http:gapi::
   :path: /db/container/foobar5/@sharing
   :path_spec: /(db)/(container)/(content)/@sharing
   :basic_auth: root:root
```

To modify, we use the same endpoint but with a `POST`.


```eval_rst
.. http:gapi::
   :path: /db/container/foobar5/@sharing
   :path_spec: /(db)/(container)/(content)/@sharing
   :method: POST
   :basic_auth: root:root
   :body: {
          "prinperm": [
            {
              "principal": "foobar",
              "permission": "guillotina.ModifyContent",
              "setting": "Allow"
            }
          ]
        }
```

There are three types of permission settings you can modify:

- prinperm: principal + permission
- prinrole: principal + role
- roleperm: role + permission

Each change can use the following settings:

- Allow : you set it on the resource and the children will inherit
- Deny : you set in on the resource and the children will inherit
- AllowSingle : you set in on the resource and the children will not inherit
- Unset : you remove the setting


## Exploring the API with Swagger

In the previous step, we installed `guillotina_swagger`. With Swagger, we can
inspect any context and explore the API.

Visit `http://localhost:8080/@docs`

![alt text](../../_static/img/swagger.png "Swagger")

click the `Authorize` button

![alt text](../../_static/img/auth-swagger.png "Swagger Auth")


The `Base API Endpoint` setting is what the current context is that you're exploring
on. If you create content at `/db/container/foobar` and want to explore that
content's API, you should change the URL. Different content types will have
different services available.



**References**

  - [REST API](../../rest/index)
  - [Behaviors](../../developer/behavior)
  - [Security](../../developer/security)
