from typing import TYPE_CHECKING

from .._content_data import Data
from .._content_provider_layer import ContentUsageLoggerMixin
from ..._content_type import ContentType
from ...delivery._data._data_provider import DataProviderLayer, Response

if TYPE_CHECKING:
    from ..._types import ExtendedParams


class Definition(ContentUsageLoggerMixin[Response[Data]], DataProviderLayer[Response[Data]]):
    """
    This class describe parameters to retrieve data for search custom instrument

    Parameters
    ----------
    access : str
        The search based on relationship to the custom instrument, for now only "owner" is supported. Can be omitted, default value is "owner"
    type_: str
        Instrument type
    limit: int
        The maximum number of instruments returned in page
    extended_params : dict, optional
        If necessary other parameters

    Examples
    --------
    >>> from lseg.data.content.custom_instruments import search
    >>> definition_search = search.Definition()
    >>> response = definition_search.get_data()
    """

    _USAGE_CLS_NAME = "CustomInstruments.SearchDefinition"

    def __init__(
        self,
        access: str = "owner",
        type_: str = None,
        limit: int = None,
        extended_params: "ExtendedParams" = None,
    ):
        from ...delivery._data._data_provider_factory import make_provider

        super().__init__(
            data_type=ContentType.CUSTOM_INSTRUMENTS_SEARCH_MULTI_REQUEST,
            one_data_provider=make_provider(ContentType.CUSTOM_INSTRUMENTS_SEARCH),
            access=access,
            type=type_,
            limit=limit,
            extended_params=extended_params,
        )
