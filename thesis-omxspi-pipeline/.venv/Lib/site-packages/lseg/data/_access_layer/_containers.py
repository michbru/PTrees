import warnings
from typing import Any, TYPE_CHECKING, Union

from .._tools import (
    ADC_FUNC_PATTERN,
    ADC_TR_PATTERN,
    cached_property,
    fields_arg_parser,
    iterator_str_arg_parser,
    get_unique_list,
)

if TYPE_CHECKING:
    from .._types import OptStrStrs, StrStrings


class Container:
    def __init__(self, raw: Any = None) -> None:
        self._raw = raw

    @property
    def raw(self) -> Any:
        return self._raw

    def __bool__(self) -> bool:
        return bool(self._raw)

    def __iter__(self):
        return iter(self._raw)


class ADCContainer(Container):
    def __init__(
        self,
        raw: Union[dict, list, None],
        fields: "FieldsContainer",
    ):
        super().__init__(raw)
        self._fields = fields

    def __bool__(self):
        is_none = self.raw in ({}, None) or (self.raw and self._fields.is_disjoint_adc)
        return not is_none


class ADCContainerEikonApproach(ADCContainer):
    def __bool__(self):
        is_none = self.raw in ({}, None)
        return not is_none


class UniverseContainer(Container):
    def __init__(self, raw: "OptStrStrs" = None) -> None:
        super().__init__(raw)
        self._adc_from_server = []

    @cached_property
    def _universe(self) -> "StrStrings":
        raw = iterator_str_arg_parser.get_list(self.raw or [])
        unique_rics = get_unique_list(raw)
        if len(unique_rics) < len(raw):
            warnings.warn("You have duplicated instruments in your input. Output will contain unique instruments only.")
        return unique_rics

    @cached_property
    def adc_from_server_and_cust_inst(self):
        return self.adc_from_server + self.cust_inst

    @cached_property
    def adc(self) -> "StrStrings":
        return [inst for inst in self._universe if not inst.startswith("S)")]

    @cached_property
    def cust_inst(self) -> "StrStrings":
        return [inst for inst in self._universe if inst.startswith("S)")]

    @cached_property
    def is_universe_expander(self):
        from ..discovery._universe_expanders._universe_expander import UniverseExpander

        return isinstance(self.raw, UniverseExpander)

    @property
    def adc_from_server(self) -> "StrStrings":
        return self._adc_from_server

    @adc_from_server.setter
    def adc_from_server(self, adc: ADCContainer):
        if not adc:
            self._adc_from_server = self.adc
        else:
            rics_from_server = list(i[0] for i in adc.raw.get("data", []))
            self._adc_from_server = get_unique_list(rics_from_server)

    def __iter__(self):
        return iter(self._universe)

    def __len__(self):
        return len(self._universe)

    def __repr__(self):
        return f"UniverseContainer({self._universe})"


class FieldsContainer(Container):
    def __init__(self, raw: "OptStrStrs" = None) -> None:
        super().__init__(raw)
        self._adc_fields: "OptStrStrs" = None
        self._pricing_fields: "OptStrStrs" = None

    def _parse(self) -> None:
        self._adc_fields = []
        self._pricing_fields = []

        for field in self._fields:
            if ADC_TR_PATTERN.match(field) or ADC_FUNC_PATTERN.match(field):
                self._adc_fields.append(field)
            else:
                self._pricing_fields.append(field)

    @cached_property
    def _fields(self) -> "StrStrings":
        raw = fields_arg_parser.get_list(self.raw or [])
        unique_fields = get_unique_list(map(str.upper, raw))
        if len(unique_fields) < len(raw):
            warnings.warn("You have duplicated fields in your input. Output will contain unique fields only.")
        return unique_fields

    @property
    def adc(self) -> "StrStrings":
        if self._adc_fields is None:
            self._parse()
        return self._adc_fields

    @property
    def pricing(self) -> "StrStrings":
        if self._pricing_fields is None:
            self._parse()
        return self._pricing_fields

    @property
    def is_no_pricing(self) -> bool:
        return not self.pricing

    @cached_property
    def is_disjoint_adc(self) -> bool:
        return set(self.adc).isdisjoint(set(self._fields))

    @cached_property
    def is_one_adc_no_pricing(self) -> bool:
        return len(self.adc) == 1 and not self.pricing

    def insert(self, index: int, value: str) -> "StrStrings":
        copy = list(self._fields)
        copy.insert(index, value)
        return copy

    def __getattr__(self, attr: str) -> Any:
        try:
            return getattr(self._fields, attr)
        except KeyError:
            raise AttributeError(attr)

    def __iter__(self):
        return iter(self._fields)

    def __repr__(self):
        return f"FieldsContainer({self._fields})"


class HPContainer(Container):
    def __init__(
        self,
        raw: Union[dict, list, None],
        axis_name: Union[str, None],
    ):
        super().__init__(raw)
        self._axis_name = axis_name

    @property
    def axis_name(self):
        return self._axis_name


class CustInstContainer(Container):
    def __init__(
        self,
        raw: Union[dict, list, None],
        axis_name: Union[str, None],
    ):
        super().__init__(raw)
        self._axis_name = axis_name

    @property
    def axis_name(self):
        return self._axis_name


class ADCAndCustInstContainer(Container):
    def __init__(self, fields_from_stream: Union[list, None], raw: Union[dict, list, None]):
        super().__init__(raw)
        self.fields_from_stream = fields_from_stream
