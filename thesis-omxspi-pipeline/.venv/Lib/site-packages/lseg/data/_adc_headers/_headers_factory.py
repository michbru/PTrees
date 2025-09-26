from typing import List, Union, Type

from ._headers import (
    HeadersALGetData,
    HeadersALGetHistory,
    HeadersCLDateAsIndex,
    HeadersCLIndex,
    RDPHeadersALGetHistory,
    UDFHeadersALGetHistory,
)
from ._headers_names import create_headers_names
from ._rules import Rules, RDPRules, UDFRules, TITLE_KEY
from .._layer_type import LayerType
from ..content._df_build_type import DFBuildType
from ..content._header_type import HeaderType
from ..content.fundamental_and_reference._data_grid_type import DataGridType


class HeadersFactory:
    rules: Rules

    @classmethod
    def _create_headers_cl_date_as_index(
        cls, data: dict, header_type: "HeaderType", date_name: str
    ) -> HeadersCLDateAsIndex:
        headers_names = create_headers_names(header_type)
        date_idxs: List[int] = []
        inst_idx = None
        date_idx = None
        headers = cls.rules.get_rdp_headers(data)
        skip_num = 0
        for idx, header in enumerate(headers):
            header_name = header[TITLE_KEY]
            if inst_idx is None and header_name == "Instrument":
                inst_idx = idx
                skip_num += 1
                continue

            if date_idx is None and header_name == "Date":
                date_idx = idx
                skip_num += 1
                continue

            headers_names.append(header)
            if cls.rules.is_date(header, header_name):
                date_idxs.append(headers.index(header) - skip_num)
        return HeadersCLDateAsIndex(date_idxs, headers_names, inst_idx, date_idx, date_name)

    @classmethod
    def _create_headers_al_get_history(
        cls, data: dict, name_key: str, headers_class: Union[Type[RDPHeadersALGetHistory], Type[UDFHeadersALGetHistory]]
    ) -> Union[RDPHeadersALGetHistory, UDFHeadersALGetHistory]:
        date_idx = None
        inst_idx = None
        date_idxs = []
        headers = cls.rules.get_headers(data)
        for idx, header in enumerate(headers):
            header_name = header[name_key]
            if cls.rules.is_date(header, header_name):
                date_idxs.append(idx)

            if inst_idx is None and header_name == "Instrument":
                inst_idx = idx
            elif date_idx is None and header_name == "Date":
                date_idx = idx

        return headers_class(headers, inst_idx, date_idx, date_idxs)

    @classmethod
    def create_headers_cl_index(cls, data: dict, header_type: "HeaderType") -> HeadersCLIndex:
        headers_names = create_headers_names(header_type)
        date_idxs = []
        for idx, header in enumerate(cls.rules.get_rdp_headers(data)):
            headers_names.append(header)
            if cls.rules.is_date(header, header[TITLE_KEY]):
                date_idxs.append(idx)

        return HeadersCLIndex(date_idxs, headers_names)

    @classmethod
    def create_headers_al_get_data(cls, data: dict, header_type: "HeaderType") -> HeadersALGetData:
        date_idxs = []
        headers_names = create_headers_names(header_type)
        for idx, header in enumerate(cls.rules.get_rdp_headers(data)):
            headers_names.append(header)
            if cls.rules.is_date(header, header[TITLE_KEY]):
                date_idxs.append(idx)

        return HeadersALGetData(date_idxs, headers_names)


class RDPHeadersFactory(HeadersFactory):
    rules = RDPRules

    @classmethod
    def create_headers_cl_date_as_index(cls, data: dict, header_type: "HeaderType") -> HeadersCLDateAsIndex:
        if header_type is HeaderType.NAME:
            date_name = "date"
        else:
            date_name = "Date"

        return cls._create_headers_cl_date_as_index(data, header_type, date_name)

    @classmethod
    def create_headers_cl_fund_and_ref_index(
        cls, build_type: DFBuildType, data: dict, header_type: "HeaderType"
    ) -> HeadersCLIndex:
        if build_type is not DFBuildType.INDEX:
            raise ValueError(f"There is no implementation for {build_type}")

        headers_names = create_headers_names(header_type)
        date_idxs = []
        for idx, header in enumerate(cls.rules.get_rdp_headers(data)):
            header_name = header[TITLE_KEY]
            if header_name == "Instrument":
                headers_names.append(header_name.capitalize())

            else:
                headers_names.append(header)

            if cls.rules.is_date(header, header_name):
                date_idxs.append(idx)

        return HeadersCLIndex(date_idxs, headers_names)

    @classmethod
    def create_headers_al_get_history(cls, data: dict) -> RDPHeadersALGetHistory:
        return cls._create_headers_al_get_history(data, TITLE_KEY, RDPHeadersALGetHistory)


class UDFHeadersFactory(HeadersFactory):
    rules = UDFRules

    @classmethod
    def create_headers_cl_date_as_index(cls, data: dict, header_type: "HeaderType") -> HeadersCLDateAsIndex:
        return cls._create_headers_cl_date_as_index(data, header_type, "Date")

    @classmethod
    def create_headers_al_get_history(cls, data: dict) -> UDFHeadersALGetHistory:
        return cls._create_headers_al_get_history(data, UDFRules.UDF_NAME_KEY, UDFHeadersALGetHistory)


create_func_by_build_type_by_data_grid_type = {
    DataGridType.UDF: {
        DFBuildType.INDEX: UDFHeadersFactory.create_headers_cl_index,
        DFBuildType.DATE_AS_INDEX: UDFHeadersFactory.create_headers_cl_date_as_index,
    },
    DataGridType.RDP: {
        DFBuildType.INDEX: RDPHeadersFactory.create_headers_cl_index,
        DFBuildType.DATE_AS_INDEX: RDPHeadersFactory.create_headers_cl_date_as_index,
    },
}


def create_headers_content_layer(
    data_grid_type: DataGridType, build_type: DFBuildType, data: dict, header_type: "HeaderType"
) -> Union[HeadersCLIndex, HeadersCLDateAsIndex]:
    create_func_by_build_type = create_func_by_build_type_by_data_grid_type.get(data_grid_type)

    if not create_func_by_build_type:
        raise TypeError(f"Unexpected data grid type. Type: {data_grid_type}")

    create_headers = create_func_by_build_type.get(build_type)

    if not create_headers:
        raise TypeError(f"Unexpected build type. Type: {build_type}")

    return create_headers(data, header_type)


def create_rdp_headers_content_layer(
    build_type: DFBuildType, data: dict, header_type: "HeaderType"
) -> Union[HeadersCLIndex, HeadersCLDateAsIndex]:
    return create_headers_content_layer(DataGridType.RDP, build_type, data, header_type)


def create_udf_headers_content_layer(
    build_type: DFBuildType, data: dict, header_type: "HeaderType"
) -> Union[HeadersCLIndex, HeadersCLDateAsIndex]:
    return create_headers_content_layer(DataGridType.UDF, build_type, data, header_type)


create_func_by_layer_by_data_grid_type = {
    DataGridType.UDF: {
        LayerType.ACCESS_GET_DATA: UDFHeadersFactory.create_headers_al_get_data,
        LayerType.ACCESS_GET_HISTORY: UDFHeadersFactory.create_headers_al_get_history,
        LayerType.CONTENT: create_udf_headers_content_layer,
    },
    DataGridType.RDP: {
        LayerType.ACCESS_GET_DATA: RDPHeadersFactory.create_headers_al_get_data,
        LayerType.ACCESS_GET_HISTORY: RDPHeadersFactory.create_headers_al_get_history,
        LayerType.CONTENT: create_rdp_headers_content_layer,
        LayerType.CONTENT_FUND_AND_REF: RDPHeadersFactory.create_headers_cl_fund_and_ref_index,
    },
}


def create_adc_headers_al_get_data(
    data_grid_type: "DataGridType", data: dict, header_type: "HeaderType"
) -> HeadersALGetData:
    create_headers = make_create_adc_headers(data_grid_type, LayerType.ACCESS_GET_DATA)
    return create_headers(data, header_type)


def create_adc_headers_al_get_history(data_grid_type: "DataGridType", data: dict) -> HeadersALGetHistory:
    create_headers = make_create_adc_headers(data_grid_type, LayerType.ACCESS_GET_HISTORY)
    return create_headers(data)


def make_create_adc_headers(data_grid_type: "DataGridType", layer_type: LayerType):
    create_func_by_layer = create_func_by_layer_by_data_grid_type.get(data_grid_type)

    if not create_func_by_layer:
        raise TypeError(f"Unexpected data grid type. Type: {data_grid_type}")

    create_func = create_func_by_layer.get(layer_type)

    if not create_func:
        raise TypeError(f"Unexpected layer type. Type: {layer_type}")

    return create_func
