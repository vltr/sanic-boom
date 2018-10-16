from sanic.request import Request
from sanic_ipware import get_client_ip


class BoomRequest(Request):
    @property
    def remote_addr(self):
        if not hasattr(self, "_remote_addr"):
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
            self._remote_addr = ip
        return self._remote_addr
