.. _marshmallowex:

===========
Marshmallow
===========

This example shows how to integrate `marshmallow <https://marshmallow.readthedocs.io/en/3.0/>`_ with ``sanic-boom``, in a way where you can have a generic type that, followed by a defined schema inside some route, will parse the ``response.json`` object given to that schema and return the created object to the handler.

Think of this as a "barebone simpler version" of `DRF <https://www.django-rest-framework.org/>`_ or any other serializer / deserializer.

.. literalinclude:: ../examples/marshmallow-integration.py
   :language: python

.. tip::
    This example is just illustrative. You can use any other ODM-like library in here. Take a look on `middle <https://middle.readthedocs.io/en/latest/>`_, another package by the same author of ``sanic-boom``.
