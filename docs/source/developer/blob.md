# Blobs

`guillotina` provides basic blob file persistency support. These blobs are still
stored in the database.


## Registering a blobs

Blobs must be registered with and store on a resource object. This is so we
can keep things keep rudimentary garbage collection on the blobs that were
created for resources.

```python

from guillotina.blob import Blob

blob = Blob(resource)
resource.blob = blob
blobfi = blob.open('w')

await blobfi.async_write(b'foobar')
assert await blobfi.async_read() == b'foobar'
```

Guillotina automatically reads and writes chunks of blob data from the database.
