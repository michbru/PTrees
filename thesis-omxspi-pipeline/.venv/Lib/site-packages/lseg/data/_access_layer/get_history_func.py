import warnings
from datetime import date, datetime, timedelta
from typing import Optional, Union, Iterable

from pandas import DataFrame

from ._containers import UniverseContainer, FieldsContainer, ADCContainer, HPContainer, CustInstContainer
from ._data_provider import get_hp_data, get_custominsts_data, get_adc_data
from ._history_df_builder import build_df_date_as_index
from ._intervals_consts import INTERVALS
from .context_collection import get_context, ContextType
from .._core.session import get_default, raise_if_closed
from .._tools import fr_datetime_adapter
from .._tools._common import get_warning_message_if_parameter_no_used_in_request
from .._types import OptDateTime
from ..content._header_type import HeaderType
from ..content.fundamental_and_reference._data_grid_type import get_data_grid_type_by_session
from ..errors import LDError
from ..usage_collection._filter_types import FilterType
from ..usage_collection._logger import get_usage_logger
from ..usage_collection._utils import ModuleName


def get_history(
    universe: Union[str, Iterable[str]],
    fields: Union[str, Iterable[str], None] = None,
    interval: Optional[str] = None,
    start: "OptDateTime" = None,
    end: "OptDateTime" = None,
    adjustments: Optional[str] = None,
    count: Optional[int] = None,
    parameters: Union[str, dict, None] = None,
    header_type: HeaderType = HeaderType.TITLE,
) -> DataFrame:
    """
    Retrieves the pricing history, as well as Fundamental and Reference data history.

    Parameters
    ----------
    universe: str | list
        Instruments to request
    fields: str | list, optional
        Fields to request
    interval: str, optional
        Date interval. Supported intervals are:
        tick, tas, taq, minute, 1min, 5min, 10min, 30min, 60min, hourly, 1h, daily,
        1d, 1D, 7D, 7d, weekly, 1W, monthly, 1M, quarterly, 3M, 6M, yearly, 1Y
    start: str or date or datetime or timedelta, optional
        The start date and timestamp of the requested history
    end: str or date or datetime or timedelta, optional
        The end date and timestamp of the requested history
    adjustments : str, optional
        Tells the system whether to apply or not apply CORAX (Corporate Actions)
        events or exchange/manual corrections or price and volume adjustment
        according to trade/quote qualifier summarization actions to historical time
        series data. Possible values are:
        exchangeCorrection, manualCorrection, CCH, CRE, RTS, RPO, unadjusted,
        qualifiers
    count : int, optional
        The maximum number of data points returned. Values range: 1 - 10000.
        Applies only to pricing fields.
    parameters: str | dict, optional
        Single global parameter key=value or dictionary
        of global parameters to request.
        Applies only to TR fields.
    header_type: HeaderType, default HeaderType.TITLE
        If HeaderType.TITLE - returns field title as column headers for data
        If HeaderType.NAME - returns field name as column headers for data
        If HeaderType.NAME_AND_TITLE - returns field name and title as column headers for data

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> get_history(universe="GOOG.O")
    >>> get_history(universe="GOOG.O", fields="tr.Revenue", interval="1Y")
    >>> get_history(
    ...     universe="GOOG.O",
    ...     fields=["BID", "ASK", "tr.Revenue"],
    ...     interval="1Y",
    ...     start="2015-01-01",
    ...     end="2020-10-01",
    ... )
    """
    session = get_default()
    raise_if_closed(session)
    logger = session.logger()

    if interval is not None and interval not in INTERVALS:
        raise ValueError(f"Not supported interval value.\nSupported intervals are: {list(INTERVALS.keys())}")

    # Library usage logging
    get_usage_logger().log_func(
        name=f"{ModuleName.ACCESS}.get_history",
        func_path=f"{__name__}.get_history",
        kwargs=dict(
            universe=universe,
            fields=fields,
            interval=interval,
            start=start,
            end=end,
            count=count,
            adjustments=adjustments,
            parameters=parameters,
            header_type=header_type,
        ),
        desc={FilterType.SYNC, FilterType.LAYER_ACCESS},
    )

    universe = UniverseContainer(universe)
    fields = FieldsContainer(fields)
    data_grid_type = get_data_grid_type_by_session(session)
    hp = get_context(ContextType.HP, universe, fields)
    adc = get_context(ContextType.GetHistoryADC, universe, fields, header_type, data_grid_type)
    cust_inst = get_context(ContextType.GetHistoryCustInst, universe, fields)
    exceptions = list()

    if adjustments is not None:
        not_applicable = []

        if cust_inst.can_get_data:
            not_applicable.append(f"custom instruments universe {cust_inst.universe.cust_inst}")

        if adc.can_get_data:
            not_applicable.append(f"fields {adc.fields.adc}")

        if not_applicable:
            warnings.warn(
                get_warning_message_if_parameter_no_used_in_request("adjustments", not_applicable=not_applicable)
            )

    universe.adc_from_server = None

    if parameters is not None:
        not_applicable = []
        applicable = []

        if cust_inst.can_get_data:
            not_applicable.append(f"custom instruments universe {universe.cust_inst}")

        if hp.can_get_data:
            if fields.pricing:
                not_applicable.append(f"fields {fields.pricing}")

            elif not fields:
                applicable.append("TR fields")

        if applicable or not_applicable:
            warnings.warn(get_warning_message_if_parameter_no_used_in_request("parameters", not_applicable, applicable))

    adc_raw = None
    if adc.can_get_data:
        adc_params = get_adc_params(start, end, interval)
        adc_params.update(parameters or {})
        adc_raw, exception_msg = get_adc_data(
            universe=universe.adc,
            fields=fields.adc,
            parameters=adc_params,
            logger=logger,
            header_type=header_type,
        )
        exceptions.append(exception_msg)

    adc_data = ADCContainer(adc_raw, fields)
    adc.adc_data = adc_data
    hp.adc_data = adc_data
    cust_inst.adc_data = adc_data
    universe.adc_from_server = adc_data

    hp_raw = None
    hp_axis_name = None
    if hp.can_get_data:
        hp_raw, hp_axis_name, exception_msg = get_hp_data(
            universe=universe.adc_from_server,
            interval=interval,
            start=start,
            end=end,
            adjustments=adjustments,
            count=count,
            fields=fields.pricing,
            logger=logger,
        )
        exceptions.append(exception_msg)

    hp_data = HPContainer(hp_raw, hp_axis_name)
    adc.hp_data = hp_data
    hp.hp_data = hp_data
    cust_inst.hp_data = hp_data

    cust_inst_raw = None
    cust_inst_axis_name = None
    if cust_inst.can_get_data:
        cust_inst_raw, cust_inst_axis_name, exception_msg = get_custominsts_data(
            universe=universe.cust_inst,
            interval=interval,
            start=start,
            end=end,
            count=count,
            logger=logger,
        )
        exceptions.append(exception_msg)

    cust_inst_data = CustInstContainer(cust_inst_raw, cust_inst_axis_name)
    adc.cust_inst_data = cust_inst_data
    hp.cust_inst_data = cust_inst_data
    cust_inst.cust_inst_data = cust_inst_data

    if exceptions and all(exceptions):
        except_msg = "\n\n".join(exceptions)
        raise LDError(message=except_msg)

    if not any({adc_data, hp_data, cust_inst_data}):
        return DataFrame()

    return build_df_date_as_index(adc, hp, cust_inst, fields, interval, logger)


def get_adc_params(
    start: Union[str, date, datetime, timedelta],
    end: Union[str, date, datetime, timedelta],
    interval: Optional[str],
) -> dict:
    """
    Gets parameters for ADC request.

    Parameters
    ----------
    start : str or date or datetime or timedelta
        Parameters start date.
    end : str or date or datetime or timedelta
        Parameters end date.
    interval : str, optional
        Interval using to calculate parameters.

    Returns
    -------
    parameters : dict
        Parameters for ADC requests.
    """
    parameters = {}
    if start is not None:
        parameters["SDate"] = fr_datetime_adapter.get_str(start)

    if end is not None:
        parameters["EDate"] = fr_datetime_adapter.get_str(end)

    if interval is not None:
        parameters["FRQ"] = INTERVALS[interval]["adc"]

    return parameters
