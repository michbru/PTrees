from collections import defaultdict

import pandas as pd

from .context_collection import ADCAndCustInstContext, GetDataADCContextType
from .._adc_headers import create_adc_headers_al_get_data
from .._core.session import get_default
from .._tools import convert_dtypes, convert_str_to_timestamp
from ..content._historical_df_builder import NotNoneList


class GetDataDFBuilderBase:
    @classmethod
    def build_common_df_with_normal_index(
        cls, adc: GetDataADCContextType, adc_and_cust_inst: "ADCAndCustInstContext"
    ) -> pd.DataFrame:
        raise NotImplementedError("build_common_df_with_normal_index is not implemented")

    @classmethod
    def build_df(cls, adc: GetDataADCContextType, adc_and_cust_inst: ADCAndCustInstContext) -> pd.DataFrame:
        logger = get_default().logger()
        logger.debug("[DataDFBuilder.build_df] Start")

        if (not adc.raw or not adc.raw["data"]) and not adc_and_cust_inst.raw:
            df = pd.DataFrame()

        elif adc_and_cust_inst.can_build_df:
            df = adc_and_cust_inst.build_df_with_normal_index()

        elif adc.can_build_df and not adc_and_cust_inst.fields_from_stream:
            df = adc.build_df_with_normal_index()

        else:
            df = cls.build_common_df_with_normal_index(adc, adc_and_cust_inst)

        logger.debug("[DataDFBuilder.build_df] End")

        if df is None:
            raise ValueError("build_config is not defined correctly")

        df.rename(columns={"instrument": "Instrument"}, inplace=True)

        return df


class GetDataDFBuilder(GetDataDFBuilderBase):
    @classmethod
    def build_common_df_with_normal_index(
        cls, adc: GetDataADCContextType, adc_and_cust_inst: "ADCAndCustInstContext"
    ) -> pd.DataFrame:
        adc_headers = create_adc_headers_al_get_data(adc.data_grid_type, adc.raw, adc.header_type)
        adc_headers_names = adc_headers.names
        fields = adc_headers_names + adc_and_cust_inst.fields_from_stream

        if not any(fields):
            return pd.DataFrame()

        if not adc_headers_names and adc_and_cust_inst.fields_from_stream:
            fields.insert(0, "Instrument")

        elif "instrument" in fields:
            fields[fields.index("instrument")] = "Instrument"

        date_idxs = adc_headers.date_idxs
        data_by_universe = defaultdict(list)
        for l in adc.raw.get("data", []):
            universe = l[0]
            l = NotNoneList(l)

            for date_idx in date_idxs:
                date_str = l[date_idx]
                l[date_idx] = convert_str_to_timestamp(date_str)

            data_by_universe[universe].append(l)

        data = []
        for line in adc_and_cust_inst.raw:
            universe = line[0]
            values = line[1:]
            if universe in data_by_universe:
                for column in data_by_universe[universe]:
                    column.extend(values)
                    data.append(column)

            else:
                tmpl = [universe] + [pd.NA] * (len(adc_headers_names) - 1) + values
                data_by_universe[universe] = tmpl
                data.append(tmpl)

        return convert_dtypes(pd.DataFrame(data, columns=fields))


class GetDataDFBuilderEikonApproach(GetDataDFBuilderBase):
    @classmethod
    def build_common_df_with_normal_index(
        cls, adc: GetDataADCContextType, cust_inst: "ADCAndCustInstContext"
    ) -> pd.DataFrame:
        adc_headers = create_adc_headers_al_get_data(adc.data_grid_type, adc.raw, adc.header_type)
        adc_headers_names = adc_headers.names
        cust_inst_fields = cust_inst.fields_from_stream
        date_idxs = adc_headers.date_idxs

        count_universes = 0
        universe_by_field = defaultdict(dict)
        for l in adc.raw.get("data", []):
            for date_idx in date_idxs:
                date_str = l[date_idx]
                l[date_idx] = convert_str_to_timestamp(date_str)

            universe = l[0]
            count_universes += 1
            for field, value in zip(adc_headers_names, NotNoneList(l)):
                universe_by_field[field][universe] = value

        for l in cust_inst.raw:
            universe = l[0]
            count_universes += 1
            for field, value in zip(["Instrument"] + cust_inst_fields, NotNoneList(l)):
                universe_by_field[field][universe] = value

        df = convert_dtypes(pd.DataFrame(universe_by_field))
        df.index = range(0, count_universes)
        return df
