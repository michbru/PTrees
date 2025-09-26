from enum import Enum, auto
from typing import TYPE_CHECKING, Union

from ._adc_and_cust_inst_context import ADCAndCustInstContext
from ._adc_context import (
    GetDataADCUDFContext,
    GetDataADCRDPContext,
    GetHistoryADCUDFContext,
    GetHistoryADCRDPContext,
)
from ._cust_inst_context import GetDataCustInstContext, GetHistoryCustInstContext
from ._hp_context import HPContext
from ...content.fundamental_and_reference._data_grid_type import DataGridType

if TYPE_CHECKING:
    from ... import HeaderType
    from .._containers import FieldsContainer, UniverseContainer


class ContextType(Enum):
    GetDataADC = auto()
    GetHistoryADC = auto()
    HP = auto()
    ADCAndCustInst = auto()
    GetDataCustInst = auto()
    GetHistoryCustInst = auto()


data_grid_type_by_context_class_by_context_type = {
    ContextType.GetDataADC: {
        DataGridType.UDF: GetDataADCUDFContext,
        DataGridType.RDP: GetDataADCRDPContext,
    },
    ContextType.GetHistoryADC: {
        DataGridType.UDF: GetHistoryADCUDFContext,
        DataGridType.RDP: GetHistoryADCRDPContext,
    },
    ContextType.HP: HPContext,
    ContextType.GetDataCustInst: GetDataCustInstContext,
    ContextType.GetHistoryCustInst: GetHistoryCustInstContext,
    ContextType.ADCAndCustInst: ADCAndCustInstContext,
}


def get_context(
    context_type: ContextType,
    universe: "UniverseContainer",
    fields: "FieldsContainer",
    header_type: "HeaderType" = None,
    data_grid_type: "DataGridType" = None,
) -> Union[
    GetDataADCUDFContext,
    GetDataADCRDPContext,
    GetHistoryADCUDFContext,
    GetHistoryADCRDPContext,
    HPContext,
    GetDataCustInstContext,
    GetHistoryCustInstContext,
    ADCAndCustInstContext,
]:
    data_grid_type_by_context_class = data_grid_type_by_context_class_by_context_type.get(context_type)

    if not data_grid_type_by_context_class:
        raise TypeError(f"Unexpected context_type. Type: {context_type}")

    if isinstance(data_grid_type_by_context_class, dict):
        context_class = data_grid_type_by_context_class.get(data_grid_type)

    else:
        context_class = data_grid_type_by_context_class

    if not context_class:
        raise TypeError(f"Unexpected type. Type: {data_grid_type}")

    if header_type is None:
        return context_class(universe, fields)

    return context_class(universe, fields, header_type)
