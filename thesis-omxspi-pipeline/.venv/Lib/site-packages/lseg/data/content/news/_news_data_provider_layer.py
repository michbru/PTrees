from typing import Callable, Optional

from .._content_provider_layer import ContentUsageLoggerMixin
from ..._core.session import get_valid_session
from ...delivery._data._data_provider import DataProviderLayer


class NewsDataProviderLayer(ContentUsageLoggerMixin, DataProviderLayer):
    _USAGE_CLS_NAME = "NewsDataProviderLayer"

    def get_data(self, session: Optional["Session"] = None):
        session = get_valid_session(session)
        response = super().get_data(session)
        return response

    async def get_data_async(
        self,
        session: Optional["Session"] = None,
        on_response: Optional[Callable] = None,
        closure: Optional[str] = None,
    ):
        session = get_valid_session(session)
        response = await super().get_data_async(session, on_response, closure)
        return response
