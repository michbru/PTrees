import warnings
from typing import Tuple

from ..._tools import convert_to_datetime
from ..._tools._utils import ensure_list
from ...delivery._data import RequestMethod
from ...delivery._data._data_provider import RequestFactory
from .._content_data_provider import ContentDataProvider
from ...delivery._data._parsed_data import ParsedData
from ...delivery._data._raw_data_parser import Parser, success_http_codes
from ...delivery._data._validators import ValidatorContainer, ContentTypeValidator


parent_orders_default_fields = [
    "Date",
    "ParentOrderID",
    "Symbol",
    "TradeCurrency",
    "Side",
    "LegSymbols",
    "Trader",
    "Account",
    "SubAccount",
    "AlgoName",
    "LP",
    "TimeZoneArrive",
    "HourArrive",
    "TimeZoneEnd",
    "HourEnd",
    "G10EM",
    "TradeSizeBucketUSDM",
    "OrderQuantity",
    "AvgChildOrderQuantityUSD",
    "OrderQuantityUSD",
    "TradeQuantityUSD",
    "TradeQuantity",
    "RemainQuantity",
    "ArrivalTime",
    "ArrivalPrice",
    "TWAPPrice",
    "LastTime",
    "LastPrice",
    "NumChildEvents",
    "NumParentEvents",
    "CurrencyPositions",
    "Duration",
    "TradeIntensity",
    "OrderIntensity",
    "RiskTransferPrice",
    "PrincipalMid",
    "DailyVolatilityPct",
    "ArrivalVolatilityPct",
    "SpreadPaidPMChildOrders",
    "AllInPrice",
    "AllInNetPrice",
    "ExecutionScore",
    "ReversalScore",
    "RiskTransferCostReportedPM",
    "RiskTransferCostStaticPM",
    "RiskTransferCostVolBumpPM",
    "RiskTransferCostModelPM",
    "RiskTransferCostTradefeedrPM",
    "AssumedRisk",
    "ArrivalMidPerfTradeBPS",
    "ArrivalMidPerfRemainBPS",
    "ArrivalMidPerfBPS",
    "TWAPMidPerfBPS",
    "ArrivalMidPerfNetBPS",
    "ArrivalMidPerfTradeNetBPS",
    "ArrivalMidPerfRemainNetBPS",
    "TWAPMidPerfNetBPS",
    "SlippageToArrivalMidTradePM",
    "SlippageToArrivalMidRemainPM",
    "SlippageToArrivalMidPM",
    "SlippageToTWAPMidPM",
    "SlippageToArrivalMidNetPM",
    "SlippageToArrivalMidTradeNetPM",
    "SlippageToArrivalMidRemainNetPM",
    "SlippageToTWAPMidNetPM",
    "SubmissionTime",
    "SubmissionPrice",
    "FirstFillTime",
    "FirstFillPrice",
    "SubmissionMidPerfBPS",
    "SubmissionMidPerfTradeBPS",
    "SubmissionMidPerfRemainBPS",
    "SubmissionMidPerfNetBPS",
    "SubmissionMidPerfTradeNetBPS",
    "SubmissionMidPerfRemainNetBPS",
    "FirstFillMidPerfBPS",
    "FirstFillMidPerfTradeBPS",
    "FirstFillMidPerfRemainBPS",
    "FirstFillMidPerfNetBPS",
    "FirstFillMidPerfTradeNetBPS",
    "FirstFillMidPerfRemainNetBPS",
]

pre_trade_forecast_default_fields = [
    "ArrivalTime",
    "Symbol",
    "OrderQuantityUSD",
    "CostOfLiquidity",
    "RiskTransferBPS",
    "ArrivalVolatilityPct",
    "ForecastModel",
    "ForecastPerfBPS",
    "ForecastPerfStdErr",
    "ForecastDurationMins",
    "ForecastDurationStdErr",
    "ForecastRiskBPS",
    "AlphaBPS",
    "InformationRatio",
    "RunsToBeatRT95",
    "RunsToBeatRT85",
]

pre_trade_forecast_default_forecast_models = ["tradefeedr/Global", "tradefeedr/Fast", "tradefeedr/Slow"]


class ParentOrdersRequestFactory(RequestFactory):
    def get_request_method(self, *, method=None, **kwargs) -> RequestMethod:
        return RequestMethod.POST

    def get_body_parameters(self, *args, body_params_config=None, **kwargs) -> dict:
        if not kwargs.get("fields"):
            kwargs["fields"] = parent_orders_default_fields

        kwargs["start"] = convert_to_datetime(kwargs["start"]).strftime("%Y-%m-%d")
        kwargs["end"] = convert_to_datetime(kwargs["end"]).strftime("%Y-%m-%d")

        filter_params = {"function": "within", "var": "Date", "pars": [kwargs.get("start"), kwargs.get("end")]}

        body_params = {"options": {"select": kwargs.get("fields"), "filter": [filter_params]}}

        return body_params

    def extend_body_parameters(self, body_parameters, extended_params=None, **kwargs):
        if not extended_params:
            return body_parameters

        # all Tradefeedr JSON request bodies start with `'options'`
        # to simplify things, we allow users to describe their `extended_params`
        # with or without this parent object `'options'` defined:
        if "options" in extended_params:
            extended_params = extended_params["options"]

        # a new within Date filter needs to replace the old one
        # the others need to be added to the list
        filters = extended_params.pop("filter", None)
        if filters:
            date_filters = []
            other_filters = []

            for filt in filters:
                if filt["function"] == "within" and filt["var"] == "Date":
                    date_filters.append(filt)
                else:
                    other_filters.append(filt)

            if len(date_filters) > 1:
                warnings.warn('Filters should only use a singular "within Date" filter. Using the last one passed.')

            if date_filters:
                body_parameters["options"]["filter"] = [date_filters[-1]]

            body_parameters["options"]["filter"].extend(other_filters)

        # add or replace the other keys
        for key, val in extended_params.items():
            body_parameters["options"][key] = val

        return body_parameters


class PreTradeForecastRequestFactory(RequestFactory):
    def get_request_method(self, *, method=None, **kwargs) -> RequestMethod:
        return RequestMethod.POST

    def get_body_parameters(self, *args, body_params_config=None, **kwargs) -> dict:
        body_params = {"options": {}}

        # filter params
        if not kwargs.get("forecast_model"):  # add default
            kwargs["forecast_model"] = pre_trade_forecast_default_forecast_models

        body_params["options"]["filter"] = [
            {"function": "in", "var": "ForecastModel", "pars": ensure_list(kwargs.get("forecast_model"))}
        ]

        # select params
        if not kwargs.get("fields"):  # add default
            kwargs["fields"] = pre_trade_forecast_default_fields

        body_params["options"]["select"] = ensure_list(kwargs.get("fields"))

        # data params
        data_params = {}
        if kwargs.get("arrival_time"):
            arrival = ensure_list(kwargs.get("arrival_time"))
            data_params["ArrivalTime"] = [convert_to_datetime(time).strftime("%Y-%m-%dT%H:%M:%S") for time in arrival]
        if kwargs.get("universe"):
            data_params["Symbol"] = ensure_list(kwargs.get("universe"))
        if kwargs.get("order_quantity_usd"):
            data_params["OrderQuantityUSD"] = ensure_list(kwargs.get("order_quantity_usd"))

        if data_params:
            body_params["options"]["data"] = data_params

        return body_params


# we need a custom parser because the tradefeedr backend is reporting json as 'text/plain'
class TradefeedrParser(Parser):
    def parse_raw_response(self, raw_response: "httpx.Response") -> Tuple[bool, ParsedData]:
        is_success = False

        if raw_response is None:
            return is_success, ParsedData({}, {})

        is_success = raw_response.status_code in success_http_codes

        # change the header to application/json because the tradefeedr api is reporting it incorrectly
        if "text/plain" in raw_response.headers["content-type"]:
            raw_response.headers["content-type"] = "application/json"

        if is_success:
            parsed_data = self.process_successful_response(raw_response)
        else:
            parsed_data = self.process_failed_response(raw_response)

        return is_success, parsed_data


pre_trade_forecast_data_provider = ContentDataProvider(
    request=PreTradeForecastRequestFactory(),
    parser=TradefeedrParser(),
    validator=ValidatorContainer(
        content_type_validator=ContentTypeValidator(allowed_content_types=["application/json", "text/plain"])
    ),
)

parent_orders_data_provider = ContentDataProvider(
    request=ParentOrdersRequestFactory(),
    parser=TradefeedrParser(),
    validator=ValidatorContainer(
        content_type_validator=ContentTypeValidator(allowed_content_types=["application/json", "text/plain"])
    ),
)
