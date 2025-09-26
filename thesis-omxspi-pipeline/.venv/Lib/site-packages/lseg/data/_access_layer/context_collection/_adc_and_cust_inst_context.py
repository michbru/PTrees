from typing import Optional, Dict, TYPE_CHECKING

from pandas import DataFrame

from ._context import GetDataContext
from ..._tools import convert_dtypes, PRICING_DATETIME_PATTERN, convert_df_columns_to_datetime_re

if TYPE_CHECKING:
    from pandas import DataFrame


class ADCAndCustInstContext(GetDataContext):
    @property
    def raw(self) -> Optional[Dict]:
        return self.adc_and_cust_inst_data and self.adc_and_cust_inst_data.raw

    @property
    def can_get_data(self) -> bool:
        return (
            bool(self.universe.adc_from_server and (not self.fields or self.fields.pricing)) or self.universe.cust_inst
        )

    @property
    def can_build_df(self) -> bool:
        return bool(self.adc_and_cust_inst_data and not (self.adc_data or self.cust_inst_data))

    @property
    def fields_from_stream(self) -> list:
        return self.adc_and_cust_inst_data.fields_from_stream

    def build_df_with_normal_index(self) -> DataFrame:
        df = DataFrame(data=self.raw, columns=("Instrument", *self.fields_from_stream))

        if len(df.columns) == 1 or not self.fields_from_stream:
            df = DataFrame()
        else:
            df = convert_dtypes(df)

        convert_df_columns_to_datetime_re(df, PRICING_DATETIME_PATTERN)
        return df
