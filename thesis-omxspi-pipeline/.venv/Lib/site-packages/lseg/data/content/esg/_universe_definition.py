from .._content_data import Data
from ..._content_type import ContentType
from ..._tools import create_repr, validate_bool_value
from .._header_type import get_header_type_by_use_field_names_in_headers
from ...delivery._data._data_provider import DataProviderLayer, Response


class Definition(DataProviderLayer[Response[Data]]):
    """
    Defines the ESG data for all available instruments.

    Parameters
    ----------
    use_field_names_in_headers: bool, optional
        Boolean that indicates whether or not to display field names in the headers.

    Examples
    --------
    >>> import asyncio
    >>> from lseg.data.content import esg
    >>> definition = esg.universe.Definition()
    >>> response = definition.get_data()

    >>> response = asyncio.run(definition.get_data_async())
    """

    def __init__(
        self,
        use_field_names_in_headers: bool = False,
    ):
        validate_bool_value(use_field_names_in_headers)
        header_type = get_header_type_by_use_field_names_in_headers(use_field_names_in_headers)

        super().__init__(
            ContentType.ESG_UNIVERSE,
            header_type=header_type,
        )

    def __repr__(self):
        return create_repr(
            self,
            middle_path="universe",
            content=f"{{closure='{self._kwargs.get('closure')}'}}",
        )
