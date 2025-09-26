import abc
from typing import Optional, List, TYPE_CHECKING

from ._context import Context, GetHistoryContext, GetDataContext
from ...content._historical_df_builder import custom_insts_builder

if TYPE_CHECKING:
    from ...content._historical_df_builder import HistoricalBuilder
    from pandas import DataFrame


class CustInstContext(Context, abc.ABC):
    @property
    def can_get_data(self) -> bool:
        return bool(self.universe.cust_inst)

    @property
    @abc.abstractmethod
    def can_build_df(self) -> bool:
        pass

    @property
    def raw(self) -> Optional[List[dict]]:
        return self.cust_inst_data and self.cust_inst_data.raw

    @property
    def dfbuilder(self) -> "HistoricalBuilder":
        return custom_insts_builder

    def build_df_with_date_as_index(self) -> "DataFrame":
        if isinstance(self.raw, dict):
            df = self.dfbuilder.build_one(self.raw, self.fields, self.cust_inst_data.axis_name)

        elif isinstance(self.raw, list):
            df = self.dfbuilder.build(self.raw, self.universe, self.fields, self.cust_inst_data.axis_name)

        else:
            raise ValueError("self.raw does not have the expected types")

        df.sort_index(ascending=False, inplace=True)
        return df

    def join_hp_df(self, hp_df: "DataFrame") -> "DataFrame":
        """
        Joins historical pricing multiindex dataframe with custom instruments dataframe.

        Parameters
        ----------
        hp_df : pd.DataFrame
            Historical pricing multiindex dataframe.

        Returns
        -------
        pd.DataFrame
            Historical pricing multiindex dataframe, joined with custom instruments
            dataframe.
        """
        from pandas import MultiIndex

        cust_df = self.dfbuilder.build(
            [self.raw] if isinstance(self.raw, dict) else self.raw,
            self.universe.cust_inst,
            self.fields,
            hp_df.index.name,
            use_multiindex=isinstance(hp_df.columns, MultiIndex),
        )
        df = hp_df.join(cust_df, how="outer")
        return df

    def join_common_df(self, common_df: "DataFrame") -> "DataFrame":
        """
        Creates dataframe with ADC, historical pricing and custom instruments data.

        Join or merge previously created ADC and historical pricing dataframe with
        custom instruments dataframe.

        Parameters
        ----------
        common_df : pd.DataFrame
            Previously created ADC and historical pricing dataframe.

        Returns
        -------
        pd.Dataframe that includes ADC, hp and custom instruments data.
        """
        cust_df = self.dfbuilder.build(
            self.raw,
            self.universe.cust_inst,
            self.fields,
            common_df.index.name,
            use_multiindex=True,
        )
        df = common_df.join(cust_df, how="outer")
        return df


class GetHistoryCustInstContext(GetHistoryContext, CustInstContext):
    @property
    def can_build_df(self) -> bool:
        return bool(self.cust_inst_data and not (self.adc_data or self.hp_data))

    @property
    def can_join_hp_df(self) -> bool:
        return bool(
            not self.adc_data and (self.hp_data and self.cust_inst_data and len(self.universe.adc_from_server) > 1)
        )


class GetDataCustInstContext(GetDataContext, CustInstContext):
    @property
    def can_build_df(self) -> bool:
        return bool(self.cust_inst_data and not self.adc_data)
