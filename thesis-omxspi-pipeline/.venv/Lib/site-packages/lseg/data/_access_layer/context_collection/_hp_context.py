from typing import Optional, Dict, TYPE_CHECKING

from ._context import GetHistoryContext
from ...content._historical_df_builder import historical_builder

if TYPE_CHECKING:
    import pandas as pd


class HPContext(GetHistoryContext):
    @property
    def can_get_data(self) -> bool:
        return bool(self.universe.adc_from_server and (not self.fields or self.fields.pricing))

    @property
    def can_build_df(self) -> bool:
        return bool(self.hp_data and not (self.adc_data or self.cust_inst_data))

    @property
    def raw(self) -> Optional[Dict]:
        return self.hp_data and self.hp_data.raw

    def build_df_with_date_as_index(self) -> "pd.DataFrame":
        if isinstance(self.raw, dict):
            df = historical_builder.build_one(self.raw, self.fields, self.hp_data.axis_name)

        elif isinstance(self.raw, list) and len(self.raw) == 1:
            df = historical_builder.build_one(self.raw[0], self.fields, self.hp_data.axis_name)

        else:
            df = historical_builder.build(self.raw, self.universe, self.fields, self.hp_data.axis_name)

        return df
