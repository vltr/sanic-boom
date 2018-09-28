import inspect


def param_parser(value: str, param: inspect.Parameter):
    annotation = param.annotation
    if annotation == inspect.Signature.empty:
        return value
    elif annotation in (int, float):
        return annotation.__call__(value)
    elif annotation == bool:
        return value.lower() in ("true", "yes", "ok")
    return value
