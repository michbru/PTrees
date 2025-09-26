import abc
from enum import Enum, auto
from typing import List, Optional

from .._tools import (
    ADC_TR_F_FUNC_PATTERN,
    ADC_TR_F_FUNC_WITH_DATE_PATTERN,
    ADC_FUNC_PATTERN,
    HEADER_NAME_DATE_PATTERN,
    HEADER_TITLE_DATE_PATTERN,
)

HP_HEADER_TYPE = "__hp_header__"
UDF_TO_RDP_ADC_HEADER_TYPE = "__udf_to_rdp_adc_header__"
WHAT_EXISTS_HEADER_TYPE = "__what_exists__"

DATE_PATTERN = "date"
DATETIME_PATTERN = "datetime"
NAME_KEY = "name"
TITLE_KEY = "title"


class Exists(Enum):
    NAME = auto()
    TITLE = auto()
    NAME_AND_TITLE = auto()
    NO_ONE = auto()


def get_what_exists(name: Optional[str], title: Optional[str]) -> Exists:
    title_exists = title is not None
    name_exists = name is not None
    if name_exists and title_exists:
        retval = Exists.NAME_AND_TITLE
    elif name_exists:
        retval = Exists.NAME
    elif title_exists:
        retval = Exists.TITLE
    else:
        retval = Exists.NO_ONE

    return retval


class Rules(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_rdp_headers(cls, data) -> List[dict]:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_headers(cls, data: dict) -> List[dict]:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def is_date(cls, header: dict, header_name: str) -> bool:
        raise NotImplementedError()


class RDPRules(Rules):
    """
    Example
    --------
    >>>
    ... {
    ...     "headers": [
    ...         {
    ...             "name": "instrument",
    ...             "title": "Instrument",
    ...             "type": "string",
    ...             "description": "The requested Instrument as defined by the user.",
    ...         },
    ...         {
    ...             "name": "date",
    ...             "title": "Date",
    ...             "type": "datetime",
    ...             "description": "Date associated with the returned data.",
    ...         },
    ...         {
    ...             "name": "TR.RevenueMean",
    ...             "title": "Currency",
    ...             "type": "string",
    ...             "description": "The statistical average of all broker ...",
    ...         },
    ...         {
    ...             "name": "TR.Revenue",
    ...             "title": "Date",
    ...             "type": "datetime",
    ...             "description": "Is used for industrial and utility companies. ...",
    ...         },
    ...     ],
    ... }
    """

    INSTRUMENT_NAME = "instrument"
    DATE_NAME = "date"

    @classmethod
    def get_rdp_headers(cls, data) -> List[dict]:
        return cls.get_headers(data)

    @classmethod
    def get_headers(cls, data: dict) -> List[dict]:
        return data.get("headers", [])

    @classmethod
    def is_date(cls, header: dict, header_name: str) -> bool:
        header_type = header.get("type")
        if header_type:
            retval = header_type in {DATETIME_PATTERN, DATE_PATTERN}
        else:
            retval = bool(HEADER_NAME_DATE_PATTERN.match(header_name))
        return retval


class UDFRules(Rules):
    """
    Example
    -------
    >>>
    ... {
    ...     "headers": [
    ...         [
    ...             {"displayName": "Instrument"},
    ...             {"displayName": "Date"},
    ...             {"displayName": "Currency", "field": "TR.REVENUEMEAN.currency"},
    ...             {"displayName": "Date", "field": "TR.REVENUE.DATE"},
    ...         ]
    ...     ],
    ... }
    """

    UDF_NAME_KEY = "displayName"
    INSTRUMENT_NAME = "Instrument"
    DATE_NAME = "Date"

    @classmethod
    def get_rdp_headers(cls, data) -> List[dict]:
        udf_headers = cls.get_headers(data)
        rdp_headers = []
        for udf_header in udf_headers:
            name = udf_header.get("field")
            title = udf_header.get("displayName")
            rdp_header = {
                UDF_TO_RDP_ADC_HEADER_TYPE: True,
                WHAT_EXISTS_HEADER_TYPE: get_what_exists(name, title),
                NAME_KEY: name or title,
                TITLE_KEY: title,
            }

            # it's because we get these headers from ld.get_history() while build common df,
            # it's related to HeadersALGetHistory class
            if HP_HEADER_TYPE in udf_header:
                rdp_header[HP_HEADER_TYPE] = udf_header[HP_HEADER_TYPE]

            rdp_headers.append(rdp_header)

        return rdp_headers

    @classmethod
    def get_headers(cls, data: dict) -> List[dict]:
        return data["headers"][0]

    @classmethod
    def is_date(cls, header: dict, header_name: str) -> bool:
        header_title = header.get(TITLE_KEY, header_name)
        header_name = header.get(NAME_KEY, header_name)
        if bool(ADC_TR_F_FUNC_PATTERN.match(header_name)):
            is_date_column = bool(ADC_TR_F_FUNC_WITH_DATE_PATTERN.match(header_name))
        else:
            is_date_column = (
                bool(HEADER_NAME_DATE_PATTERN.match(header_name))
                and bool(HEADER_TITLE_DATE_PATTERN.match(header_title))
                and not bool(ADC_FUNC_PATTERN.match(header_title))
            )
        return is_date_column
