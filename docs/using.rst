.. _using:

=======================
Using ``middle-schema``
=======================

For now, ``middle-schema`` only supports the generation of `OpenAPI 3.0 <https://swagger.io/docs/specification/about>`_ schemas for models based on `middle <https://middle.readthedocs.io/en/latest/>`_. It should be used to generate schemas for documentation and/or client generation, independently if you're going to use it as reference or integrate with a real world framework or API.

OpenAPI 3.0
-----------

To generate OpenAPI 3.0 compliant schemas (and components), you should import ``middle_schema.openapi`` to generate a ``OpenAPI`` instance, that contains two attributes:

* ``specification``: the actual specification of the model given (as a ``dict``);
* ``components``: the components created for the given model (as a ``dict``);

.. attention::

    Both attributes can have different outputs given changes in the configuration, as can be seen in the next topic.

Configuration
-------------

``middle-schema`` has two configuration options regarding the schema and components generation that can be applied to recursive models or enum classes, mostly to switch between transforming them into components or leave them inline.

``openapi_enum_as_component``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Default:** ``True`` (boolean)

With this option enabled, all enum types will be generated as components and will end up inside the ``components`` attribute of your ``OpenAPI`` instance, with only references (as ``{"$ref": "#/components/schema/MyEnumName"}``) inside the specification.

.. code-block:: pycon

    >>> import enum
    >>> import json
    >>> import middle
    >>> from middle_schema.openapi import parse

    >>> @enum.unique
    ... class TestIntEnum(enum.IntEnum):
    ...     TEST_1 = 1
    ...     TEST_2 = 2
    ...     TEST_3 = 3

    >>> class TestModel(middle.Model):
    ...     some_enum = middle.field(
    ...         type=TestIntEnum, description="Some test enumeration"
    ...     )

    >>> api = parse(TestModel)
    >>> json.dumps(api.specification, indent=4)
    {
        "$ref": "#/components/schemas/TestModel"
    }

    >>> json.dumps(api.components, indent=4)
    {
        "TestIntEnum": {
            "type": "integer",
            "format": "int64",
            "choices": [
                1,
                2,
                3
            ]
        },
        "TestModel": {
            "type": "object",
            "properties": {
                "some_enum": {
                    "$ref": "#/components/schemas/TestIntEnum",
                    "description": "Some test enumeration"
                }
            },
            "required": [
                "some_enum"
            ]
        }
    }

    >>> middle.config.openapi_enum_as_component = False

    >>> api = parse(TestModel)
    >>> json.dumps(api.specification, indent=4)
    {
        "$ref": "#/components/schemas/TestModel"
    }

    >>> json.dumps(api.components, indent=4)
    {
        "TestModel": {
            "type": "object",
            "properties": {
                "some_enum": {
                    "type": "integer",
                    "format": "int64",
                    "description": "Some test enumeration",
                    "choices": [
                        1,
                        2,
                        3
                    ]
                }
            },
            "required": [
                "some_enum"
            ]
        }
    }

``openapi_model_as_component``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Default:** ``True`` (boolean)

With this option enabled, all ``middle.Model`` subclasses will be generated as components and will end up inside the ``components`` attribute of your ``OpenAPI`` instance, with only references (as ``{"$ref": "#/components/schema/AnotherModel"}``) inside the specification.

.. code-block:: pycon

    >>> import json
    >>> import middle
    >>> from middle_schema.openapi import parse

    >>> class InnerModel(middle.Model):
    ...     name = middle.field(
    ...         type=str, min_length=3, description="The person name"
    ...     )
    ...     age = middle.field(type=int, minimum=18, description="The person age")

    >>> class TestModel(middle.Model):
    ...     person = middle.field(
    ...         type=InnerModel, description="The person to access this resource"
    ...     )
    ...     active = middle.field(
    ...         type=bool, description="If the resource is active"
    ...     )

    >>> api = parse(TestModel)
    >>> json.dumps(api.specification, indent=4)
    {
        "$ref": "#/components/schemas/TestModel"
    }

    >>> json.dumps(api.components, indent=4)
    {
        "InnerModel": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 3,
                    "description": "The person name"
                },
                "age": {
                    "type": "integer",
                    "format": "int64",
                    "minimum": 18,
                    "description": "The person age"
                }
            },
            "required": [
                "name",
                "age"
            ],
            "description": "The person to access this resource"
        },
        "TestModel": {
            "type": "object",
            "properties": {
                "person": {
                    "$ref": "#/components/schemas/InnerModel"
                },
                "active": {
                    "type": "boolean",
                    "description": "If the resource is active"
                }
            },
            "required": [
                "person",
                "active"
            ]
        }
    }

    >>> middle.config.openapi_model_as_component = False

    >>> api = parse(TestModel)
    >>> json.dumps(api.specification, indent=4)
    {
        "type": "object",
        "properties": {
            "person": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "minLength": 3,
                        "description": "The person name"
                    },
                    "age": {
                        "type": "integer",
                        "format": "int64",
                        "minimum": 18,
                        "description": "The person age"
                    }
                },
                "required": [
                    "name",
                    "age"
                ],
                "description": "The person to access this resource"
            },
            "active": {
                "type": "boolean",
                "description": "If the resource is active"
            }
        },
        "required": [
            "person",
            "active"
        ]
    }

    >>> json.dumps(api.components, indent=4)
    {}

.. attention::

    Every ``middle.Model`` object is intended to be generated as a component, that's why the specification (when the config key ``openapi_model_as_component`` is ``True``) ends up being just a ``$ref`` to a component and, being ``False``, would generate all models and inner models inline, as one.
