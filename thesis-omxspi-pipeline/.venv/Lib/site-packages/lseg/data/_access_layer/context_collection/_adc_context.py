import abc
from typing import Optional, Dict, Union

import pandas as pd

from ._context import GetHistoryContext, GetDataContext, Context
from .._history_df_builder import UniqueListOfLists
from ...content._df_builder import get_adc_dfbuilder
from ...content.fundamental_and_reference._data_grid_type import DataGridType


class ADCContext(Context, abc.ABC):
    data_grid_type: DataGridType

    @property
    @abc.abstractmethod
    def can_build_df(self) -> bool:
        pass

    @property
    def can_get_data(self) -> bool:
        if not self.fields.adc:
            return False

        return bool(self.universe.adc) and not (
            self.universe.is_universe_expander and self.fields.pricing and self.fields.is_disjoint_adc
        )

    @property
    def raw(self) -> Optional[Dict]:
        return self.adc_data.raw if self.adc_data else None

    def build_df_with_normal_index(self) -> pd.DataFrame:
        df = get_adc_dfbuilder(self.data_grid_type).build_index(
            self.raw,
            self.header_type,
            use_multiindex=False,
        )

        return df

    def build_df_with_date_as_index(self) -> pd.DataFrame:
        data = UniqueListOfLists(self.raw["data"])
        self.raw["data"] = data
        self.raw["totalRowsCount"] = len(data)
        df = get_adc_dfbuilder(self.data_grid_type).build_date_as_index(
            self.raw,
            self.header_type,
            use_multiindex=False,
        )
        return df


class GetHistoryADCContextMixin(GetHistoryContext, ADCContext, abc.ABC):
    @property
    def can_build_df(self) -> bool:
        return bool(self.adc_data and not (self.hp_data or self.cust_inst_data))


class ADCUDFContextMixin(abc.ABC):
    data_grid_type = DataGridType.UDF


class ADCRDPContextMixin(abc.ABC):
    data_grid_type = DataGridType.RDP


class GetHistoryADCUDFContext(GetHistoryADCContextMixin, ADCUDFContextMixin):
    pass


class GetHistoryADCRDPContext(GetHistoryADCContextMixin, ADCRDPContextMixin):
    pass


class GetDataADCContextMixin(GetDataContext, ADCContext, abc.ABC):
    @property
    def can_build_df(self) -> bool:
        return bool(self.adc_data and not self.cust_inst_data)


class GetDataADCUDFContext(GetDataADCContextMixin, ADCUDFContextMixin):
    pass


class GetDataADCRDPContext(GetDataADCContextMixin, ADCRDPContextMixin):
    pass


GetDataADCContextType = Union[GetDataADCUDFContext, GetDataADCRDPContext]
GetHistoryADCContextType = Union[GetHistoryADCUDFContext, GetHistoryADCRDPContext]
