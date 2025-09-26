import abc
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from ... import HeaderType
    from .._containers import (  # noqa: F401
        ADCContainer,
        CustInstContainer,
        FieldsContainer,
        HPContainer,
        UniverseContainer,
        ADCAndCustInstContainer,
    )


@dataclass
class Context(abc.ABC):
    universe: "UniverseContainer"
    fields: "FieldsContainer"
    header_type: "HeaderType" = None
    adc_data: Optional["ADCContainer"] = None
    cust_inst_data: Optional["CustInstContainer"] = None


@dataclass
class GetDataContext(Context):
    adc_and_cust_inst_data: "ADCAndCustInstContainer" = None


@dataclass
class GetHistoryContext(Context):
    hp_data: Union["HPContainer", None] = None
