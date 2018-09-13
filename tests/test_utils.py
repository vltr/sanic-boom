import inspect

from sanic_boom import param_parser


def test_int():
    def myfunc(value: int):
        return value

    sig = inspect.signature(myfunc)
    value_param = sig.parameters.get("value")
    assert myfunc(20) == param_parser("20", value_param)


def test_float():
    def myfunc(value: float):
        return value

    sig = inspect.signature(myfunc)
    value_param = sig.parameters.get("value")
    assert myfunc(3.14) == param_parser("3.14", value_param)


def test_bool():
    def myfunc(value: bool):
        return value

    sig = inspect.signature(myfunc)
    value_param = sig.parameters.get("value")
    assert myfunc(True) == param_parser("true", value_param)
    assert myfunc(True) == param_parser("True", value_param)
    assert myfunc(True) == param_parser("TRUE", value_param)
    assert myfunc(True) == param_parser("ok", value_param)
    assert myfunc(True) == param_parser("Ok", value_param)
    assert myfunc(True) == param_parser("OK", value_param)
    assert myfunc(True) == param_parser("YES", value_param)
    assert myfunc(True) == param_parser("yes", value_param)
    assert myfunc(True) == param_parser("Yes", value_param)
    assert myfunc(False) == param_parser("false", value_param)
    assert myfunc(False) == param_parser("False", value_param)
    assert myfunc(False) == param_parser("No", value_param)
    assert myfunc(False) == param_parser("NO", value_param)
    assert myfunc(False) == param_parser("FOO", value_param)
    assert myfunc(False) == param_parser("foo", value_param)


def test_default():
    def myfunc(value: str):
        return value

    sig = inspect.signature(myfunc)
    value_param = sig.parameters.get("value")
    assert myfunc("foo") == param_parser("foo", value_param)


def test_empty():
    def myfunc(value):
        return value

    sig = inspect.signature(myfunc)
    value_param = sig.parameters.get("value")
    assert myfunc("foo") == param_parser("foo", value_param)
    assert myfunc(20) == param_parser(20, value_param)
    assert myfunc(True) == param_parser(True, value_param)
