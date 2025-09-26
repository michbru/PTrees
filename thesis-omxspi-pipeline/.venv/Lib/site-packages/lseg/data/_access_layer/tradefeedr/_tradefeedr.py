import pandas as pd
from typing import Union, Dict, List

from ...content.tradefeedr import ParentOrderDefinition, PreTradeForecastDefinition


def get_fx_algo_pre_trade_forecast(
    universe: Union[str, List[str]],
    order_quantity_usd: Union[float, int, List[float], List[int]],
    arrival_time: Union[str, List[str]],
    fields: Union[str, List[str], None] = None,
    forecast_model: Union[str, List[str], None] = None,
) -> pd.DataFrame:
    """
    Fetches pre-trade forecast for given parameters.

    Parameters
    ----------
    universe: str | List[str]
        Instrument(s) to request.
    order_quantity_usd: float | int | List[int] | List[float]
        List of order quantities in USD.
    arrival_time: str | List[str]
        Arrival time(s).
        String format is: '%Y-%m-%dT%H:%M:%S'. e.g. '2024-01-20T15:04:05'.
    fields: str | List[str], optional
        Field(s) to request.
    forecast_model: str | List[str], optional
        Forecast model(s). Possible values are "tradefeedr/Global", "tradefeedr/Fast", "tradefeedr/Slow".

    Returns
    -------
    pd.DataFrame

    Examples
    --------
    >>> import lseg.data as ld
    >>> ld.tradefeedr.get_fx_algo_pre_trade_forecast(
    ...     universe=["EURUSD", "USDJPY"],
    ...     order_quantity_usd=[50e6, 30e6],
    ...     arrival_time=["2023-08-10 11:52", "2023-08-10 12:30"]
    ... )
    """

    definition = PreTradeForecastDefinition(
        universe=universe,
        order_quantity_usd=order_quantity_usd,
        arrival_time=arrival_time,
        fields=fields,
        forecast_model=forecast_model,
    )
    return definition.get_data().data.df


def get_fx_algo_parent_orders(
    start: str, end: str, fields: Union[str, List[str], None] = None, extended_params: Union[None, Dict] = None
) -> pd.DataFrame:
    """
    Fetches parent orders for given parameters.

    Parameters
    ----------
    start: str
        Start of the period to get data for
    end: str
        End of the period to get data for
    fields: str | List[str], optional
        Field(s) to request, if no fields are passed a default is used
    extended_params:
        extra paremeters for the backend request

    Returns
    -------
    pd.Dataframe

    Examples
    --------
    >>> import lseg.data as ld
    >>> ld.tradefeedr.get_fx_algo_pre_trade_forecast(
    ...     start='2020-01-01',
    ...     end='2024-01-01'
    ... )
    """

    definition = ParentOrderDefinition(start=start, end=end, fields=fields, extended_params=extended_params)
    return definition.get_data().data.df
