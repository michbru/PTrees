from typing import TYPE_CHECKING

from ._definition_base import BaseDefinition, OptRowHeaders
from .._content_data import Data
from .._content_provider_layer import ContentUsageLoggerMixin
from .._header_type import HeaderType
from ..._content_type import ContentType
from ...delivery._data._data_provider import Response

if TYPE_CHECKING:
    from ..._types import ExtendedParams, OptDict, StrStrings


class Definition(ContentUsageLoggerMixin[Response[Data]], BaseDefinition):
    """
    Defines the Fundamental and Reference data to retrieve.

    Parameters:
    ----------
    universe : str or list of str
        Single instrument or list of instruments.
    fields : str or list of str
        Single field or list of fields.
    parameters : dict, optional
        Fields global parameters.
    row_headers : str, list of str, list of RowHeaders enum
        Output/layout parameters to add to the underlying request. Put headers to rows in the response.
    extended_params : dict, optional
        Specifies the parameters that will be merged with the request.
    header_type : HeaderType, optional
        Specifies the header key to use in the response.

    Examples
    --------
    >>> from lseg.data.content import fundamental_and_reference
    >>> definition = fundamental_and_reference.Definition(["IBM"], ["TR.Volume"])
    >>> definition.get_data()

    Using get_data_async

    >>> import asyncio
    >>> task = definition.get_data_async()
    >>> response = asyncio.run(task)
    """

    _USAGE_CLS_NAME = "FundamentalAndReference.Definition"

    def __init__(
        self,
        universe: "StrStrings",
        fields: "StrStrings",
        parameters: "OptDict" = None,
        row_headers: "OptRowHeaders" = None,
        extended_params: "ExtendedParams" = None,
        header_type: HeaderType = HeaderType.TITLE,
    ):
        super().__init__(ContentType.DEFAULT, universe, fields, header_type, parameters, row_headers, extended_params)
