# Web sockets


`guillotina` has support for web sockets built into the api.


## Flow

1. Make a reqeust to `@wstoken` to get your interaction token
2. Use token given there with `@ws?token=`
3. Send data over the web socket connection in the form of: {"op": "GET", "value": "path/to/service"}
