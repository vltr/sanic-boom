from cgi import parse_header
from http.cookies import SimpleCookie
from io import BytesIO
from urllib.parse import parse_qs, urlunparse

from httptools import parse_url
from multidict import istr
from sanic.exceptions import InvalidUsage
from sanic.log import error_logger
from sanic.request import (DEFAULT_HTTP_CONTENT_TYPE, RequestParameters,
                           json_loads, parse_multipart_form)
from sanic_ipware import get_client_ip

# --------------------------------------------------------------------------- #
# used headers
# --------------------------------------------------------------------------- #

_H_CONTENT_TYPE = istr("content-type")
_H_COOKIE = istr("cookie")
_H_UPGRADE = istr("upgrade")
_H_HOST = istr("host")

# --------------------------------------------------------------------------- #
# the request class
# --------------------------------------------------------------------------- #


class BoomRequest(dict):
    """Properties of an HTTP request such as URL, headers, etc."""

    __slots__ = (
        "__weakref__",
        "_data",
        "_parsed_url",
        "body",
        "headers",
        "method",
        "raw_url",
        "stream",
        "transport",
        "uri_template",
        "version",
    )

    def __init__(self, url_bytes, headers, version, method, transport):
        self.raw_url = url_bytes
        # TODO: see https://github.com/huge-success/sanic/issues/1329
        self._parsed_url = parse_url(url_bytes)

        self.headers = headers
        self.version = version
        self.method = method
        self.transport = transport
        self.stream = None
        self._data = {}

    def __repr__(self):
        if self.method is None or not self.path:
            return "<BoomRequest>"
        return "<BoomRequest: {1} {2}>".format(self.method, self.path)

    def __bool__(self):  # noqa
        if self.transport:
            return True
        return False

    # ----------------------------------------------------------------------- #
    # methods
    # ----------------------------------------------------------------------- #

    def body_append(self, data):
        if "_body" not in self._data:
            self._data["_body"] = BytesIO()
        if self._data["_body"].closed:
            raise IOError("the body is already closed")  # TODO fix
        self._data["_body"].write(data)

    def body_finish(self):
        if "_body" in self._data:
            self.body = self._data["_body"].getvalue()
            self._data["_body"].close()
        else:
            self.body = b""

    def _load_json(self, loads=json_loads):
        try:
            self._data["parsed_json"] = loads(self.body)
        except Exception:
            if not self.body:
                return
            raise InvalidUsage("Failed parsing the body as json")

    def _get_address(self):
        _socket = self.transport.get_extra_info("peername") or (None, None)
        self._data["_socket"] = _socket
        self._data["_ip"] = _socket[0]
        self._data["_port"] = _socket[1]

    # ----------------------------------------------------------------------- #
    # properties
    # ----------------------------------------------------------------------- #

    @property
    def app(self):
        if "_app" in self._data:
            return self._data["_app"]
        return None

    @app.setter
    def app(self, value):
        if "_app" not in self._data:
            self._data["_app"] = value

    @property
    def json(self):
        if "parsed_json" not in self._data:
            self._load_json()
        return self._data["parsed_json"]

    @property
    def form(self):
        if "parsed_form" not in self._data:
            self._data["parsed_form"] = RequestParameters()
            self._data["parsed_files"] = RequestParameters()
            content_type = self.headers.get(
                _H_CONTENT_TYPE, DEFAULT_HTTP_CONTENT_TYPE
            )
            content_type, parameters = parse_header(content_type)
            try:
                if content_type == "application/x-www-form-urlencoded":
                    self._data["parsed_form"] = RequestParameters(
                        parse_qs(self.body.decode("utf-8"))
                    )
                elif content_type == "multipart/form-data":
                    # TODO: Stream this instead of reading to/from memory
                    boundary = parameters["boundary"].encode("utf-8")
                    parsed_form, parsed_files = parse_multipart_form(
                        self.body, boundary
                    )
                    self._data["parsed_form"] = parsed_form
                    self._data["parsed_files"] = parsed_files
            except Exception:
                error_logger.exception("Failed when parsing form")
        return self._data["parsed_form"]

    @property
    def files(self):
        if "parsed_files" not in self._data:
            self.form  # compute form to get files
        return self._data["parsed_files"]

    @property
    def args(self):
        if "parsed_args" not in self._data:
            if self.query_string:
                self._data["parsed_args"] = RequestParameters(
                    parse_qs(self.query_string)
                )
            else:
                self._data["parsed_args"] = RequestParameters()
        return self._data["parsed_args"]

    @property
    def raw_args(self):
        return {k: v[0] for k, v in self.args.items()}

    @property
    def cookies(self):
        if "_cookies" not in self._data:
            cookie = self.headers.get(_H_COOKIE)
            _cookies = {}
            if cookie is not None:
                cookies = SimpleCookie()
                cookies.load(cookie)
                _cookies = {
                    name: cookie.value for name, cookie in cookies.items()
                }
            self._data["_cookies"] = _cookies
        return self._data["_cookies"]

    @property
    def ip(self):
        if "_socket" not in self._data:
            self._get_address()
        return self._data["_ip"]

    @property
    def port(self):
        if "_socket" not in self._data:
            self._get_address()
        return self._data["_port"]

    @property
    def socket(self):
        if "_socket" not in self._data:
            self._get_address()
        return self._data["_socket"]

    @property
    def remote_addr(self):
        if "_remote_addr" not in self._data:
            proxy_count = None
            proxy_trusted_ips = None
            request_header_order = None
            if self.app and self.app.config:
                proxy_count = getattr(
                    self.app.config, "IPWARE_PROXY_COUNT", None
                )
                proxy_trusted_ips = getattr(
                    self.app.config, "IPWARE_PROXY_TRUSTED_IPS", None
                )
                request_header_order = getattr(
                    self.app.config, "IPWARE_REQUEST_HEADER_ORDER", None
                )
            ip, _ = get_client_ip(
                self,
                proxy_count=proxy_count,
                proxy_trusted_ips=proxy_trusted_ips,
                request_header_order=request_header_order,
            )
            self._data["_remote_addr"] = ip
        return self._data["_remote_addr"]

    @property
    def scheme(self):
        if "_scheme" not in self._data:
            _scheme = "http"
            if (
                self.app
                and self.app.websocket_enabled
                and self.headers.get(_H_UPGRADE) == "websocket"
            ):
                _scheme = "ws"

            if self.transport.get_extra_info("sslcontext"):
                _scheme += "s"

            self._data["_scheme"] = _scheme

        return self._data["_scheme"]

    @property
    def host(self):
        # it appears that httptools doesn't return the host
        # so pull it from the headers
        return self.headers.get(_H_HOST, "")

    @property
    def content_type(self):
        return self.headers.get(_H_CONTENT_TYPE, DEFAULT_HTTP_CONTENT_TYPE)

    @property
    def path(self):
        if "_path" not in self._data:
            self._data["_path"] = self._parsed_url.path.decode("utf-8")
        return self._data["_path"]

    @property
    def query_string(self):
        if "_query_string" not in self._data:
            if self._parsed_url.query:
                self._data["_query_string"] = self._parsed_url.query.decode(
                    "utf-8"
                )
            else:
                self._data["_query_string"] = ""
        return self._data["_query_string"]

    @property
    def url(self):
        return urlunparse(
            (self.scheme, self.host, self.path, None, self.query_string, None)
        )
