import warnings
from typing import Iterable, Union, List

from pandas import DataFrame

from ._containers import (
    ADCContainer,
    FieldsContainer,
    ADCAndCustInstContainer,
    UniverseContainer,
    ADCContainerEikonApproach,
)
from ._data_df_builder import GetDataDFBuilder, GetDataDFBuilderEikonApproach
from ._data_provider import get_data_from_stream, get_adc_data_safe, get_adc_data_safe_eikon_approach
from .context_collection import get_context, ContextType, GetDataADCContextType, ADCAndCustInstContext
from .._core.session import get_default, raise_if_closed, SessionType, Session
from .._errors import LDError
from .._tools._common import get_warning_message_if_parameter_no_used_in_request
from ..content._header_type import HeaderType
from ..content.fundamental_and_reference._data_grid_type import get_data_grid_type_by_session, DataGridType
from ..usage_collection import FilterType, get_usage_logger
from ..usage_collection._utils import ModuleName


def get_data(
    universe: Union[str, Iterable[str]],
    fields: Union[str, Iterable[str]],
    parameters: Union[str, dict, None] = None,
    header_type: HeaderType = HeaderType.TITLE,
) -> DataFrame:
    """
    Retrieves pricing snapshots, as well as Fundamental and Reference data.

    Parameters
    ----------
    universe: str | list
        Instruments to request
    fields: str | list
        Fields to request
    parameters: str | dict, optional
        Single key=value global parameter or dictionary of global parameters to request
    header_type: HeaderType, default HeaderType.TITLE
        If HeaderType.TITLE - returns field title as column headers for data
        If HeaderType.NAME - returns field name as column headers for data
        If HeaderType.NAME_AND_TITLE - returns field name and title as column headers for data

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> get_data(universe=['IBM.N', 'VOD.L'], fields=['BID', 'ASK'])
    >>> get_data(
    ...     universe=['GOOG.O', 'AAPL.O'],
    ...     fields=['TR.EV','TR.EVToSales'],
    ...     parameters = {'SDate': '0CY', 'Curn': 'CAD'}
    ... )
    """
    session = get_default()
    raise_if_closed(session)

    # Library usage logging
    get_usage_logger().log_func(
        name=f"{ModuleName.ACCESS}.get_data",
        func_path=f"{__name__}.get_data",
        kwargs=dict(
            universe=universe,
            fields=fields,
            parameters=parameters,
            header_type=header_type,
        ),
        desc={FilterType.SYNC, FilterType.LAYER_ACCESS},
    )

    universe = UniverseContainer(universe)

    use_streaming_for_pricing_fields = session.config.get_param("apis.data.datagrid.use_streaming_for_pricing_fields")
    data_grid_type = get_data_grid_type_by_session(session)
    can_use_eikon_approach = (
        session.type == SessionType.DESKTOP
        and data_grid_type == DataGridType.UDF
        and use_streaming_for_pricing_fields is False
    )

    if can_use_eikon_approach:
        return _get_data_eikon_approach(universe, fields, parameters, header_type, session)

    return _get_data(universe, fields, parameters, header_type, session)


def raise_if_all(exceptions: List[str]):
    if exceptions and all(exceptions):
        raise LDError(message="\n\n".join(exceptions))


def _get_data_eikon_approach(
    universe: UniverseContainer,
    fields: Union[str, Iterable[str]],
    parameters: Union[str, dict, None],
    header_type: HeaderType,
    session: "Session",
) -> DataFrame:
    if not fields:
        return DataFrame()

    exceptions = list()
    fields = FieldsContainer(fields)
    data_grid_type = get_data_grid_type_by_session(session)

    cust_inst: ADCAndCustInstContext = get_context(ContextType.ADCAndCustInst, universe, fields)
    adc: GetDataADCContextType = get_context(ContextType.GetDataADC, universe, fields, header_type, data_grid_type)

    fields_from_stream, stream_data = None, None
    if universe.cust_inst:
        fields_from_stream, stream_data, exception_msg = get_data_from_stream(
            universe.cust_inst,
            fields.adc + fields.pricing,
            session,
        )
        exceptions.append(exception_msg)

    cust_inst_data = ADCAndCustInstContainer(fields_from_stream, stream_data)
    adc.adc_and_cust_inst_data = cust_inst_data
    cust_inst.adc_and_cust_inst_data = cust_inst_data

    adc_raw = None
    if universe.adc:
        adc_raw, exception_msg = get_adc_data_safe_eikon_approach(
            universe.adc,
            fields.adc + fields.pricing,
            parameters,
            header_type,
            session,
        )
        exceptions.append(exception_msg)

    raise_if_all(exceptions)

    adc_data = ADCContainerEikonApproach(adc_raw, fields)
    adc.adc_data = adc_data
    cust_inst.adc_data = adc_data

    return GetDataDFBuilderEikonApproach.build_df(adc, cust_inst)


def _get_data(
    universe: UniverseContainer,
    fields: Union[str, Iterable[str]],
    parameters: Union[str, dict, None],
    header_type: HeaderType,
    session: "Session",
) -> DataFrame:
    data_grid_type = get_data_grid_type_by_session(session)
    logger = session.logger()

    exceptions = list()
    fields = FieldsContainer(fields)
    adc_and_cust_inst: ADCAndCustInstContext = get_context(ContextType.ADCAndCustInst, universe, fields)
    adc: GetDataADCContextType = get_context(ContextType.GetDataADC, universe, fields, header_type, data_grid_type)

    universe.adc_from_server = None

    if parameters:
        not_applicable = []
        applicable = []

        if universe.cust_inst:
            not_applicable.append(f"custom instruments universe {universe.cust_inst}")

        if fields.pricing:
            not_applicable.append(f"fields {fields.pricing}")

        elif not fields:
            applicable.append("TR fields")

        if not_applicable or applicable:
            warnings.warn(get_warning_message_if_parameter_no_used_in_request("parameters", not_applicable, applicable))

    adc_raw = None
    if adc.can_get_data:
        adc_raw, exception_msg = get_adc_data_safe(
            {
                "universe": universe.adc,
                "fields": fields.adc,
                "parameters": parameters,
                "header_type": header_type,
            },
            logger,
        )
        exceptions.append(exception_msg)

    adc_data = ADCContainer(adc_raw, fields)
    adc.adc_data = adc_data
    adc_and_cust_inst.adc_data = adc_data
    universe.adc_from_server = adc_data

    fields_from_stream, stream_data = None, None
    if adc_and_cust_inst.can_get_data:
        fields_from_stream, stream_data, exception_msg = get_data_from_stream(
            universe.adc_from_server_and_cust_inst, fields.pricing, session
        )
        exceptions.append(exception_msg)

    raise_if_all(exceptions)

    adc_and_cust_inst_data = ADCAndCustInstContainer(fields_from_stream, stream_data)
    adc.adc_and_cust_inst_data = adc_and_cust_inst_data
    adc_and_cust_inst.adc_and_cust_inst_data = adc_and_cust_inst_data

    return GetDataDFBuilder.build_df(adc, adc_and_cust_inst)
