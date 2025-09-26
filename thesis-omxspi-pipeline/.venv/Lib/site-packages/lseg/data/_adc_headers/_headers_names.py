from typing import Union

from ._rules import NAME_KEY, HP_HEADER_TYPE, UDF_TO_RDP_ADC_HEADER_TYPE, WHAT_EXISTS_HEADER_TYPE, Exists, TITLE_KEY
from ..content._header_type import HeaderType


class HeadersNames(list):
    def get_name(self, header: dict) -> str:
        raise NotImplementedError()

    def process_hdr(self, hdr: dict) -> str:
        if HP_HEADER_TYPE in hdr:
            name = hdr[NAME_KEY]

        elif UDF_TO_RDP_ADC_HEADER_TYPE in hdr:
            exists = hdr[WHAT_EXISTS_HEADER_TYPE]
            if exists == Exists.NAME:
                name = hdr[NAME_KEY]

            elif exists == Exists.TITLE:
                name = hdr[TITLE_KEY]

            elif exists == Exists.NAME_AND_TITLE:
                name = self.get_name(hdr)

            else:
                name = ""

        else:
            name = self.get_name(hdr)

        return name

    def append(self, obj: Union[dict, str]) -> None:
        if isinstance(obj, dict):
            super().append(self.process_hdr(obj))
        else:
            super().append(obj)

    @property
    def columns(self) -> list:
        return self

    def get_index_name(self, unique_insts=None):
        if unique_insts is None:
            index_name = self.pop()
        else:
            index_name = unique_insts.pop()

        return index_name


class HeadersNames_Name(HeadersNames):
    get_name = lambda self, hdr: hdr[NAME_KEY]


class HeadersNames_Title(HeadersNames):
    get_name = lambda self, hdr: hdr[TITLE_KEY]


class HeadersNames_NameAndTitle(HeadersNames):
    delim = "|"

    def get_name(self, hdr: dict) -> str:
        return f"{hdr[NAME_KEY]}{self.delim}{hdr[TITLE_KEY]}"


header_type_to_headers_names_class = {
    HeaderType.NAME: HeadersNames_Name,
    HeaderType.TITLE: HeadersNames_Title,
    HeaderType.NAME_AND_TITLE: HeadersNames_NameAndTitle,
}


def create_headers_names(header_type: Union[HeaderType, str]) -> HeadersNames:
    headers_names_class = header_type_to_headers_names_class.get(header_type)

    if not headers_names_class:
        raise TypeError(f"Unexpected header_type: {header_type}")

    return headers_names_class()
