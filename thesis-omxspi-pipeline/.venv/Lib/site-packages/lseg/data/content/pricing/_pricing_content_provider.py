from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, List, Callable

import pandas as pd

from .._content_data import Data
from .._content_data_provider import ContentDataProvider
from .._content_response_factory import ContentResponseFactory
from .._error_parser import ErrorParser
from ..._tools import (
    PRICING_DATETIME_PATTERN,
    ValueParamItem,
    fields_arg_parser,
    universe_arg_parser,
    cached_property,
    convert_df_columns_to_datetime_re,
    convert_dtypes,
    get_unique_list,
)
from ...delivery._data._data_provider import ContentValidator, RequestFactory, ValidatorContainer
from ...delivery._stream.stream_cache import StreamCache

if TYPE_CHECKING:
    from ...delivery._data._data_provider import ParsedData


# ---------------------------------------------------------------------------
#   Response factory
# ---------------------------------------------------------------------------


class PriceCache:
    def __init__(self, data: List[dict]):
        self._data = {item.get("Key", {}).get("Name"): item for item in data}
        self._cache = {key: StreamCache(d) for key, d in self._data.items()}

    def keys(self):
        return self._cache.keys()

    def values(self):
        return self._cache.values()

    def items(self):
        return self._cache.items()

    def __iter__(self):
        return iter(self.values())

    def __getitem__(self, name):
        if name not in self.keys():
            raise KeyError(f"{name} not in PriceCache")

        return self._cache[name]

    def __len__(self):
        return len(self.keys())

    def __str__(self):
        return str(self._data)


status_code_to_value = {"NotEntitled": "#N/P", "NotFound": "#N/F"}


def pricing_build_df(raw: List[dict], universe: list, fields: list, **_) -> pd.DataFrame:
    if not fields:
        fields = get_unique_list(key for item in raw for key in item.get("Fields", {}).keys())

    data = []
    num_fields = len(fields)
    for idx, item in enumerate(raw):
        inst_name = universe[idx]
        if item["Type"] == "Status":
            value = status_code_to_value.get(item["State"]["Code"])
            values = [value] * num_fields
            data.append([inst_name, *values])
        else:
            row = [inst_name]
            for field in fields:
                value = item["Fields"].get(field)
                value = pd.NA if value is None else value
                row.append(value)
            data.append(row)

    df = pd.DataFrame(data=data, columns=["Instrument", *fields])
    convert_df_columns_to_datetime_re(df, PRICING_DATETIME_PATTERN)
    df = convert_dtypes(df)
    return df


@dataclass
class PricingData(Data):
    @cached_property
    def prices(self):
        return PriceCache(self.raw)


# ---------------------------------------------------------------------------
#   Request factory
# ---------------------------------------------------------------------------
pricing_query_params = [
    ValueParamItem("universe", function=partial(universe_arg_parser.get_str, delim=",")),
    ValueParamItem("fields", function=partial(fields_arg_parser.get_str, delim=",")),
]


class PricingRequestFactory(RequestFactory):
    @property
    def query_params_config(self):
        return pricing_query_params


# ---------------------------------------------------------------------------
#   Content data validator
# ---------------------------------------------------------------------------


class PricingContentValidator(ContentValidator):
    @cached_property
    def validators(self) -> List[Callable[["ParsedData"], bool]]:
        return [self.status_is_not_error]


# ---------------------------------------------------------------------------
#   Data provider
# ---------------------------------------------------------------------------

pricing_data_provider = ContentDataProvider(
    request=PricingRequestFactory(),
    response=ContentResponseFactory(data_class=PricingData),
    parser=ErrorParser(),
    validator=ValidatorContainer(content_validator=PricingContentValidator()),
)
