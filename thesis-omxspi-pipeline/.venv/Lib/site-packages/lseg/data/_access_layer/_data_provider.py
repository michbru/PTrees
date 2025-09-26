from typing import Dict, List, Optional, Union, Tuple, TYPE_CHECKING, Iterable

from ._intervals_consts import INTERVALS, EVENTS_INTERVALS
from ._mixed_streams import MixedStreams
from .._log import is_debug
from .._tools import DEBUG
from ..content import custom_instruments, fundamental_and_reference, historical_pricing
from ..content._get_adc_data import get_adc_data as get_response_data
from ..content._header_type import HeaderType
from ..content.fundamental_and_reference._definition_eikon_approach import EikonApproachDefinition
from ..errors import ScopeError, LDError

if TYPE_CHECKING:
    from .._core.session import Session
    from logging import Logger


def get_hp_data(
    universe: List[str],
    fields: List[str],
    interval: Optional[str],
    start: Optional[str],
    end: Optional[str],
    adjustments: Optional[str],
    count: Optional[int],
    logger: "Logger",
) -> Tuple[Union[Dict, None], Union[str, None], Union[str, None]]:
    """
    Gets historical pricing raw data.

    Parameters
    ----------
    universe : str / list
        Instruments to request.
    fields : str / list
        Fields for request.
    interval: str, optional
        Consolidation interval.
    start : str, optional
        Start date.
    end : str, optional
        End date.
    adjustments : str, optional
        Adjustments for request.
    count : int, optional
        Number of data rows.
    logger : Logger
        Session logger.

    Returns
    -------
    raw : dict or None:
        Historical pricing raw data.
    axis_name : str or None
        Axis name for data.
    exception_msg : str or None
        API exception message.
    """
    raw = None
    axis_name = None
    exception_msg = None
    if interval in EVENTS_INTERVALS:
        definition = historical_pricing.events.Definition(
            universe=universe,
            eventTypes=INTERVALS[interval]["event_types"],
            start=start,
            end=end,
            adjustments=adjustments,
            count=count,
            fields=fields,
        )

    else:
        interval = INTERVALS[interval]["pricing"] if interval is not None else interval

        definition = historical_pricing.summaries.Definition(
            universe=universe,
            interval=interval,
            start=start,
            end=end,
            adjustments=adjustments,
            count=count,
            fields=fields,
        )

    try:
        response = definition.get_data()
        DEBUG and logger.debug(f"HISTORICAL_PRICING --->\n{response.data.df.to_string()}\n")
        raw = response.data.raw
        axis_name = response._kwargs["axis_name"]
        if isinstance(raw, dict):
            raw = [raw]
    except LDError as hp_error:
        DEBUG and logger.exception(f"Failure sending request with {definition}, error:{hp_error}")
        exception_msg = hp_error.message
    except Exception as exc:
        DEBUG and logger.exception(f"Failure sending request with {definition}. {exc}")
        exception_msg = str(exc)

    return raw, axis_name, exception_msg


def get_adc_data(
    universe: List[str],
    fields: List[str],
    parameters: dict,
    logger: "Logger",
    header_type: HeaderType,
) -> Tuple[Union[Dict, None], Union[str, None]]:
    raw = None
    exception_msg = None

    definition = fundamental_and_reference.Definition(
        universe=universe,
        fields=fields,
        parameters=parameters,
        row_headers="date",
        header_type=header_type,
    )
    try:
        response = definition.get_data()
        raw = response.data.raw
        DEBUG and logger.debug(f"ADC --->\n{response.data.df.to_string()}\n")
    except ScopeError as scope_error:
        DEBUG and logger.exception(f"Failure sending request with {definition}. {scope_error}")
        exception_msg = (
            f"Insufficient scope for key={scope_error.key}, "
            f"method={scope_error.method} failed.\n "
            f"Required scope: {' OR '.join(map(str, scope_error.required_scope))}\n "
            f"Missing scopes: {' OR '.join(map(str, scope_error.missing_scopes))}"
        )
    except LDError as adc_error:
        DEBUG and logger.exception(f"Failure sending request with {definition}. {adc_error}")
        exception_msg = adc_error.message
    except Exception as exc:
        DEBUG and logger.exception(f"Failure sending request with {definition}. {exc}")
        exception_msg = str(exc)

    return raw, exception_msg


def get_adc_data_safe(params: dict, logger: "Logger") -> Tuple[dict, Union[str, None]]:
    """
    Gets data from ADC and handles exceptions, if necessary.

    Parameters
    ----------
    params : dict
        Input parameters with instruments and fields.
    logger : Logger
        Session logger.

    Returns
    -------
    raw : dict
        ADC raw data.
    exception_msg : str or None
        API exception message, if returned.

    """
    raw = {}
    exception_msg = None

    try:
        data = get_response_data(params, logger)
        raw = data.raw
    except ScopeError as scope_error:
        DEBUG and logger.exception(
            f"Failure sending request with {params.get('fields', '')} for {params['universe']}. {scope_error}"
        )
        exception_msg = (
            f"Insufficient scope for key={scope_error.key}, "
            f"method={scope_error.method} failed.\n "
            f"Required scope: {' OR '.join(map(str, scope_error.required_scope))}\n "
            f"Missing scopes: {' OR '.join(map(str, scope_error.missing_scopes))}"
        )
    except LDError as adc_error:
        DEBUG and logger.exception(
            f"Failure sending request with {params.get('fields', '')} for {params['universe']}. {adc_error}"
        )
        exception_msg = adc_error.message
    except Exception as exc:
        DEBUG and logger.exception(
            f"Failure sending request with {params.get('fields', '')} for {params['universe']}. {str(exc)}"
        )
        exception_msg = str(exc)
    return raw, exception_msg


def get_adc_data_safe_eikon_approach(
    universe: Union[str, Iterable[str]],
    fields: Union[str, Iterable[str], None],
    parameters: Union[str, dict, None],
    header_type: HeaderType,
    session: "Session",
) -> Tuple[Union[dict, None], Union[str, None]]:
    exception_msg = None
    raw = None

    try:
        definition = EikonApproachDefinition(universe, fields, parameters, header_type)
        response = definition.get_data(session)
        raw = response.data.raw
    except ScopeError as scope_error:
        exception_msg = (
            f"Insufficient scope for key={scope_error.key}, "
            f"method={scope_error.method} failed.\n "
            f"Required scope: {' OR '.join(map(str, scope_error.required_scope))}\n "
            f"Missing scopes: {' OR '.join(map(str, scope_error.missing_scopes))}"
        )
    except LDError as adc_error:
        exception_msg = adc_error.message
    except Exception as exc:
        exception_msg = str(exc)

    return raw, exception_msg


def get_custominsts_data(
    universe: List[str],
    interval: Optional[str],
    start: Optional[str],
    end: Optional[str],
    count: Optional[int],
    logger: "Logger",
) -> Tuple[Union[Dict, None], Union[str, None], Union[str, None]]:
    """
    Get custom instruments data.

    Parameters
    ----------
    universe : list of str
        Instruments for request.
    interval : str, optional
        Interval for request.
    start : str, optional
        Start date.
    end : str, optional
        End date.
    count : int, optional
        Maximum number of retrieved data.
    logger : Logger
        Session logger.

    Returns
    -------
    raw : dict or None:
        Custom instruments raw data.
    axis_name : str or None
        Axis name for data.
    exception_msg : str or None
        API exception message.
    """
    raw = None
    exception_msg = None
    axis_name = None
    if interval in EVENTS_INTERVALS:
        definition = custom_instruments.events.Definition(
            universe=universe,
            start=start,
            end=end,
            count=count,
        )

    else:
        interval = INTERVALS[interval]["pricing"] if interval is not None else interval
        definition = custom_instruments.summaries.Definition(
            universe=universe,
            interval=interval,
            start=start,
            end=end,
            count=count,
        )

    try:
        response = definition.get_data()
        raw = response.data.raw
        axis_name = response._kwargs["axis_name"]
        DEBUG and logger.debug(f"CUSTOMINSTS --->\n{response.data.df.to_string()}\n")
    except LDError as cust_error:
        DEBUG and logger.exception(f"Failure sending request with {definition}. {cust_error}")
        exception_msg = cust_error.message
    except Exception as exc:
        DEBUG and logger.exception(f"Failure sending request with {definition}. {exc}")
        exception_msg = str(exc)

    return raw, axis_name, exception_msg


def get_data_from_stream(
    universe: Union[str, List[str]], user_fields: Union[str, List[str]], session: "Session"
) -> Tuple[Union[List[str], None], Union[list, None], Union[str, None]]:
    """
    Gets pricing and custom instruments data from stream.

    Parameters
    ----------
    universe : str or list of str
        Instruments using to get data.
    user_fields : str or list of str
        Instruments fields for request.
    session: Session
        Session instance.

    Returns
    -------
    columns : list of str or None
        Names of data columns, if returned.
    data : dict or None
        Pricing raw data, if returned.
    exception_msg : str or None
        API exception message, if returned.

    """
    logger = session.logger()
    logger.info(f"Requesting pricing info for fields={user_fields} via websocket")
    stream = MixedStreams(universe=universe, fields=user_fields, session=session)
    fields, server_fields, data, exception_msg = None, None, None, None

    try:
        stream.open(with_updates=False)
        server_fields = stream.get_field_keys_from_record()

        if user_fields:
            fields = list(filter(lambda user_field: user_field in server_fields, user_fields))

        else:
            fields = server_fields

        data = stream.get_data_with_convert_types(fields)

    except Exception as exc:
        exception_msg = str(exc)
        is_debug(logger) and logger.debug(f"Failure retrieving data for {stream._universe}: {exception_msg}")

    finally:
        stream.close()

    return fields, data, exception_msg
