from functools import reduce
from typing import List

import pandas as pd

from .._content_type import ContentType
from .._tools import get_unique_list, has_any_substrings, DATE_SUBSTRINGS
from ..content._universe_stream import _UniverseStream
from ..content._universe_streams import _UniverseStreams


class MixedStreams(_UniverseStreams):
    def __init__(self, *args, **kwargs):
        super().__init__(owner=self, *args, **kwargs, content_type=ContentType.NONE)

    def _get_pricing_stream(self, name) -> _UniverseStream:
        return _UniverseStream(
            content_type=ContentType.STREAMING_PRICING,
            name=name,
            session=self._session,
            owner=self,
            fields=self.fields,
            service=self._service,
            extended_params=self._extended_params,
        )

    def _get_custom_instruments_stream(self, name) -> _UniverseStream:
        return _UniverseStream(
            content_type=ContentType.STREAMING_CUSTOM_INSTRUMENTS,
            name=name,
            session=self._session,
            owner=self,
            fields=self.fields,
            service=self._service,
            extended_params=self._extended_params,
        )

    def create_stream_by_name(self, name) -> _UniverseStream:
        if name.startswith("S)"):
            stream = self._get_custom_instruments_stream(name)
        else:
            stream = self._get_pricing_stream(name)
        return stream

    def get_field_keys_from_record(self) -> List[str]:
        return get_unique_list(reduce(lambda l, stream: l + stream.record.get_fields_keys(), self.values(), []))

    def get_data_with_convert_types(self, fields) -> list:
        return [[stream.name] + convert_types(fields, stream.record.get_fields()) for stream in self.values()]


def convert_types(columns: List[str], stream_data: dict) -> list:
    values = []

    for column in columns:
        try:
            value = stream_data[column]
        except KeyError:
            value = pd.NA
        else:
            if value is None or value == "":
                value = pd.NA
            elif has_any_substrings(column, DATE_SUBSTRINGS):
                try:
                    value = pd.to_datetime(value)
                except ValueError:
                    pass

        values.append(value)

    return values
