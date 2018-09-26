import inspect

from multidict import istr

_REMOTE_ADDR_X_FORWARDED_FOR = istr("x-forwarded-for")
_REMOTE_ADDR_X_REAL_IP = istr("x-real-ip")
_REMOTE_ADDR_X_CLIENT_IP = istr("x-client-ip")
_REMOTE_ADDR_X_FORWARDED = istr("x-forwarded")
_REMOTE_ADDR_X_CLUSTER_CLIENT_IP = istr("x-cluster-client-ip")
_REMOTE_ADDR_FORWARDED_FOR = istr("forwarded-for")
_REMOTE_ADDR_FORWARDED = istr("forwarded")
_REMOTE_ADDR_VIA = istr("via")
# https://support.cloudflare.com/hc/en-us/articles/206776727-What-is-True-Client-IP-
_REMOTE_ADDR_TRUE_CLIENT_IP = istr("true-client-ip")

_PRECEDENCE_ORDER = (
    _REMOTE_ADDR_X_FORWARDED_FOR,
    _REMOTE_ADDR_X_REAL_IP,
    _REMOTE_ADDR_X_CLIENT_IP,
    _REMOTE_ADDR_X_FORWARDED,
    _REMOTE_ADDR_X_CLUSTER_CLIENT_IP,
    _REMOTE_ADDR_FORWARDED_FOR,
    _REMOTE_ADDR_FORWARDED,
    _REMOTE_ADDR_VIA,
    _REMOTE_ADDR_TRUE_CLIENT_IP
)


def param_parser(value: str, param: inspect.Parameter):
    annotation = param.annotation
    if annotation == inspect.Signature.empty:
        return value
    elif annotation in (int, float):
        return annotation.__call__(value)
    elif annotation == bool:
        return value.lower() in ("true", "yes", "ok")
    return value


def get_remote_addr(headers):  # not yet the best solution
    if _REMOTE_ADDR_X_FORWARDED_FOR in headers:
        xff = headers.get(_REMOTE_ADDR_X_FORWARDED_FOR)
        if xff.find(",") > -1:
            xff = [a.strip() for a in xff.split(",") if a.strip() != ""][0]
        return xff
    elif _REMOTE_ADDR_X_REAL_IP in headers:
        return headers.get(_REMOTE_ADDR_X_REAL_IP)
    return ""
