import socket
from cgi import parse_header
from http.cookies import SimpleCookie
from io import BytesIO
from urllib.parse import parse_qs
from urllib.parse import urlunparse

from httptools import parse_url
from multidict import istr
from sanic.exceptions import InvalidUsage
from sanic.log import error_logger
from sanic.request import DEFAULT_HTTP_CONTENT_TYPE
from sanic.request import RequestParameters
from sanic.request import json_loads
from sanic.request import parse_multipart_form

from sanic_boom.utils import get_remote_addr

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


class Request(dict):
    """Properties of an HTTP request such as URL, headers, etc."""

    __slots__ = (
        "__weakref__",
        "_body",
        "_cookies",
        "_ip",
        "_path",
        "_parsed_url",
        "_port",
        "_query_string",
        "_remote_addr",
        "_socket",
        "_scheme",
        "_app",
        "body",
        "headers",
        "method",
        "parsed_args",
        "parsed_files",
        "parsed_form",
        "parsed_json",
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
        # self.app = None

        self.headers = headers
        self.version = version
        self.method = method
        self.transport = transport

        # Init but do not inhale
        # self._body = BytesIO()
        # self.body = None
        # self.parsed_json = None
        # self.parsed_form = None
        # self.parsed_files = None
        # self.parsed_args = None
        # self.uri_template = None
        # self._cookies = None
        # self.stream = None
        # self._path = None
        # self._query_string = None
        # self._scheme = None

    def __has(self, key):
        return hasattr(self, key)

    def __repr__(self):
        if self.method is None or not self.path:
            return "<Request>"
        return "<Request: {1} {2}>".format(self.method, self.path)

    def __bool__(self):
        if self.transport:
            return True
        return False

    # ----------------------------------------------------------------------- #
    # methods
    # ----------------------------------------------------------------------- #

    def body_append(self, data):
        if not self.__has("_body"):
            self._body = BytesIO()
        if self._body.closed:
            raise IOError("the body is already closed")  # TODO fix
        self._body.write(data)

    def body_finish(self):
        if self.__has("_body"):
            self.body = self._body.getvalue()
            self._body.close()
        else:
            self.body = b''

    # ----------------------------------------------------------------------- #
    # properties
    # ----------------------------------------------------------------------- #

    @property
    def app(self):
        if self.__has("_app"):
            return self._app
        return None

    @app.setter
    def app(self, value):
        if self.app is None:
            self._app = value

    @property
    def json(self):
        if not self.__has("parsed_json"):
            self._load_json()

        return self.parsed_json

    def _load_json(self, loads=json_loads):
        try:
            self.parsed_json = loads(self.body)
        except Exception:
            if not self.body:
                return
            raise InvalidUsage("Failed parsing the body as json")

    @property
    def form(self):
        if not self.__has("parsed_form"):
            self.parsed_form = RequestParameters()
            self.parsed_files = RequestParameters()
            content_type = self.headers.get(
                _H_CONTENT_TYPE, DEFAULT_HTTP_CONTENT_TYPE
            )
            content_type, parameters = parse_header(content_type)
            try:
                if content_type == "application/x-www-form-urlencoded":
                    self.parsed_form = RequestParameters(
                        parse_qs(self.body.decode("utf-8"))
                    )
                elif content_type == "multipart/form-data":
                    # TODO: Stream this instead of reading to/from memory
                    boundary = parameters["boundary"].encode("utf-8")
                    self.parsed_form, self.parsed_files = parse_multipart_form(
                        self.body, boundary
                    )
            except Exception:
                error_logger.exception("Failed when parsing form")

        return self.parsed_form

    @property
    def files(self):
        if not self.__has("parsed_files"):
            self.form  # compute form to get files

        return self.parsed_files

    @property
    def args(self):
        if not self.__has("parsed_args"):
            if self.query_string:
                self.parsed_args = RequestParameters(
                    parse_qs(self.query_string)
                )
            else:
                self.parsed_args = RequestParameters()
        return self.parsed_args

    @property
    def raw_args(self):
        return {k: v[0] for k, v in self.args.items()}

    @property
    def cookies(self):
        if not self.__has("_cookies"):
            cookie = self.headers.get(_H_COOKIE)
            if cookie is not None:
                cookies = SimpleCookie()
                cookies.load(cookie)
                self._cookies = {
                    name: cookie.value for name, cookie in cookies.items()
                }
            else:
                self._cookies = {}
        return self._cookies

    @property
    def ip(self):
        if not self.__has("_socket"):
            self._get_address()
        return self._ip

    @property
    def port(self):
        if not self.__has("_socket"):
            self._get_address()
        return self._port

    @property
    def socket(self):
        if not self.__has("_socket"):
            self._get_address()
        return self._socket

    def _get_address(self):
        sock = self.transport.get_extra_info("socket")

        if sock.family == socket.AF_INET:
            self._socket = self.transport.get_extra_info("peername") or (
                None,
                None,
            )
            self._ip, self._port = self._socket
        elif sock.family == socket.AF_INET6:
            self._socket = self.transport.get_extra_info("peername") or (
                None,
                None,
                None,
                None,
            )
            self._ip, self._port, *_ = self._socket
        else:
            self._ip, self._port = (None, None)

    @property
    def remote_addr(self):
        """Attempt to return the original client ip based on X-Forwarded-For.

        :return: original client ip.
        """
        if not self.__has("_remote_addr"):
            self._remote_addr = get_remote_addr(self.headers)
        return self._remote_addr

    @property
    def scheme(self):
        if not self.__has("_scheme"):
            if (
                self.app.websocket_enabled
                and self.headers.get(_H_UPGRADE) == "websocket"
            ):
                self._scheme = "ws"
            else:
                self._scheme = "http"

            if self.transport.get_extra_info("sslcontext"):
                self._scheme += "s"

        return self._scheme

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
        if not self.__has("_path"):
            self._path = self._parsed_url.path.decode("utf-8")
        return self._path

    @property
    def query_string(self):
        if not self.__has("_query_string"):
            if self._parsed_url.query:
                self._query_string = self._parsed_url.query.decode("utf-8")
            else:
                self._query_string = ""
        return self._query_string

    @property
    def url(self):
        return urlunparse(
            (self.scheme, self.host, self.path, None, self.query_string, None)
        )
