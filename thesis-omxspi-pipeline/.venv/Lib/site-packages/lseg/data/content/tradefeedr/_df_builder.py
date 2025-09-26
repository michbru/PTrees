import pandas as pd
import json

from lseg.data._tools import convert_df_columns_to_datetime, convert_dtypes


def build_tradefeedr_df(content_data, **_) -> pd.DataFrame:
    if type(content_data) is str:
        content_data_json = json.loads(content_data)
        df = pd.DataFrame(content_data_json["result"])
    else:
        df = pd.DataFrame(content_data["result"])

    convert_df_columns_to_datetime(df, "ArrivalTime", utc=True, delete_tz=True, unit="ms")
    df = convert_dtypes(df)

    return df
