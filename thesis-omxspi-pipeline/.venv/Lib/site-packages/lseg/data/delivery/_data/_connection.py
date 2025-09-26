from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import httpx
    from ._request import Request
    from ..._core.session import Session


class HttpSessionConnection:
    def send(self, request: "Request", session: "Session", *_, auto_retry=False, **__) -> "httpx.Response":
        request.auto_retry = auto_retry
        return session.http_request(request)

    async def send_async(self, request: "Request", session: "Session", *_, auto_retry=False, **__) -> "httpx.Response":
        request.auto_retry = auto_retry
        return await session.http_request_async(request)
