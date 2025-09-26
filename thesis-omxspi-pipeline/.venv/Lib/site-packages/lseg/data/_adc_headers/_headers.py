from dataclasses import dataclass
from typing import List, Dict

from ._headers_names import HeadersNames
from ._rules import NAME_KEY, HP_HEADER_TYPE


@dataclass
class HeadersCLIndex:
    """
    HeadersCLIndex == HeadersContentLayerIndex
    """

    date_idxs: List[int]
    names: HeadersNames


@dataclass
class HeadersCLDateAsIndex(HeadersCLIndex):
    """
    HeadersCLDateAsIndex == HeadersContentLayerDateAsIndex
    """

    inst_idx: int
    date_idx: int
    date_name: str


@dataclass
class HeadersALGetData:
    """
    HeadersALGetData == HeadersAccessLayerGetData
    """

    date_idxs: List[int]
    names: HeadersNames


class HeadersALGetHistory(list):
    """
    HeadersALGetHistory == HeadersAccessLayerGetHistory
    """

    inst_idx: int
    date_idx: int
    date_idxs: List[int]

    def __init__(self, headers: List[dict], inst_idx: int, date_idx: int, date_idxs: List[int]) -> None:
        super().__init__(headers)  # copy
        self.inst_idx = inst_idx
        self.date_idx = date_idx
        self.date_idxs = date_idxs

    def __add__(self, dicts: List[Dict]) -> "HeadersALGetHistory":
        for d in dicts:
            self.append(d)
        return self

    def transform_hp_headers_to_adc(self, hp_headers: List[Dict]) -> List[Dict]:
        raise NotImplementedError()

    def set_headers_to(self, data: dict, headers: List[dict]) -> dict:
        raise NotImplementedError()


class RDPHeadersALGetHistory(HeadersALGetHistory):
    def transform_hp_headers_to_adc(self, hp_headers: List[Dict]) -> List[Dict]:
        return [
            {
                HP_HEADER_TYPE: True,
                NAME_KEY: header.get(NAME_KEY),
                "title": header.get(NAME_KEY),
            }
            for header in hp_headers
        ]

    def set_headers_to(self, data: dict, headers: List[dict]) -> dict:
        data["headers"] = headers
        return data


class UDFHeadersALGetHistory(HeadersALGetHistory):
    def transform_hp_headers_to_adc(self, hp_headers: List[Dict]) -> List[Dict]:
        return [
            {
                HP_HEADER_TYPE: True,
                "field": header.get(NAME_KEY),
                "displayName": header.get(NAME_KEY),
            }
            for header in hp_headers
        ]

    def set_headers_to(self, data: dict, headers: List[dict]) -> dict:
        data["headers"] = [headers]
        return data
