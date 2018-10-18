.. _sanicjwtex:

=========
sanic-jwt
=========

This example shows how to integrate `sanic-jwt <https://sanic-jwt.readthedocs.io/en/latest/>`_ with ``sanic-boom``, using a *layered* middleware, to determine that from a specific route onwards, every user will have to be authenticated - so you won't need to declare anything else in your endpoints to protect them.

It also figures the usage of a component that is solely required by another component, as a simple example.

.. literalinclude:: ../examples/sanic-jwt-integration.py
   :language: python

Testing
~~~~~~~

Calling the root endpoint:

::

    $ curl -v http://127.0.0.1:8000/
    *   Trying 127.0.0.1...
    * TCP_NODELAY set
    * Connected to 127.0.0.1 (127.0.0.1) port 8000 (#0)
    > GET / HTTP/1.1
    > Host: 127.0.0.1:8000
    > User-Agent: curl/7.61.1
    > Accept: */*
    >
    < HTTP/1.1 200 OK
    < Connection: keep-alive
    < Keep-Alive: 5
    < Content-Length: 2
    < Content-Type: text/plain; charset=utf-8
    <
    * Connection #0 to host 127.0.0.1 left intact
    OK

So far so good, this was the expected result. Now, let's try to access a restricted endpoint (by the code, any endpoint starting with ``/restricted/`` will have authentication required), without a token:

::

    $ curl -v http://127.0.0.1:8000/restricted/foo
    *   Trying 127.0.0.1...
    * TCP_NODELAY set
    * Connected to 127.0.0.1 (127.0.0.1) port 8000 (#0)
    > GET /restricted/foo HTTP/1.1
    > Host: 127.0.0.1:8000
    > User-Agent: curl/7.61.1
    > Accept: */*
    >
    < HTTP/1.1 401 Unauthorized
    < Connection: keep-alive
    < Keep-Alive: 5
    < Content-Length: 76
    < Content-Type: application/json
    <
    * Connection #0 to host 127.0.0.1 left intact
    {"reasons":["Authorization header not present."],"exception":"Unauthorized"}

But, but ... Is that black magic? Actually, no. This is really straightforward. Now, let's finally authenticate a user:

::

    $ curl -v http://127.0.0.1:8000/auth -d '{"username":"user1","password":"abcxyz"}'
    *   Trying 127.0.0.1...
    * TCP_NODELAY set
    * Connected to 127.0.0.1 (127.0.0.1) port 8000 (#0)
    > POST /auth HTTP/1.1
    > Host: 127.0.0.1:8000
    > User-Agent: curl/7.61.1
    > Accept: */*
    > Content-Length: 40
    > Content-Type: application/x-www-form-urlencoded
    >
    * upload completely sent off: 40 out of 40 bytes
    < HTTP/1.1 200 OK
    < Connection: keep-alive
    < Keep-Alive: 5
    < Content-Length: 140
    < Content-Type: application/json
    <
    * Connection #0 to host 127.0.0.1 left intact
    {"access_token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE1Mzk4OTUxODh9.FF2zld_RM01nhkFLVPIa6SRg6PZkGCCW6rFjrpTkc0o"}

Great, we have an ``access_token``! Let's try to access our restricted endpoint again:

::

    $ curl -v http://127.0.0.1:8000/restricted/foo -H "Authorization: Bearer <token>"
    *   Trying 127.0.0.1...
    * TCP_NODELAY set
    * Connected to 127.0.0.1 (127.0.0.1) port 8000 (#0)
    > GET /restricted/foo HTTP/1.1
    > Host: 127.0.0.1:8000
    > User-Agent: curl/7.61.1
    > Accept: */*
    > Authorization: Bearer <token>
    >
    < HTTP/1.1 200 OK
    < Connection: keep-alive
    < Keep-Alive: 5
    < Content-Length: 1
    < Content-Type: text/plain; charset=utf-8
    <
    * Connection #0 to host 127.0.0.1 left intact
    1

And our return is ``1``, as is the ``user_id`` parameter for ``user1``. You can try to get a token for each user (``user2``, ``user3`` and ``user4``) and execute this last endpoint. The result should be the number of the user.

And what about the layered middleware? You just need to implement one argument in a middleware and all endpoints starting with it will run it, and in this example, will require an authenticated user. Another example? Sure!

::

    $ curl -v http://127.0.0.1:8000/restricted/bar -H "Authorization: Bearer <token>"
    *   Trying 127.0.0.1...
    * TCP_NODELAY set
    * Connected to 127.0.0.1 (127.0.0.1) port 8000 (#0)
    > GET /restricted/bar HTTP/1.1
    > Host: 127.0.0.1:8000
    > User-Agent: curl/7.61.1
    > Accept: */*
    > Authorization: Bearer <token>
    >
    < HTTP/1.1 200 OK
    < Connection: keep-alive
    < Keep-Alive: 5
    < Content-Length: 19
    < Content-Type: text/plain; charset=utf-8
    <
    * Connection #0 to host 127.0.0.1 left intact
    this is restricted!

Well, a lot of boilerplate code has just vanished ¯\\_(ツ)_/¯
