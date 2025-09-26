from ..._tools import ADC_TR_PATTERN, ADC_FUNC_PATTERN, ParamItem, ValueParamItem, cached_property
from ...delivery._data import RequestMethod
from ...delivery._data._data_provider import RequestFactory, Request

parameters = ParamItem("parameters")

rdp_universe = ParamItem("universe")
rdp_fields = ValueParamItem("fields", function=lambda fields, **kwargs: list(map(str.upper, fields)))
rdp_layout = ValueParamItem(
    "layout",
    "output",
    is_true=lambda layout, **kwargs: isinstance(layout, dict) and layout.get("output"),
    function=lambda layout, **kwargs: layout["output"],
)

udf_universe = ParamItem("universe", "instruments")
udf_fields = ValueParamItem(
    "fields",
    function=lambda fields, **kwargs: [
        {"name": i.upper()} for i in fields if ADC_TR_PATTERN.match(i) or ADC_FUNC_PATTERN.match(i)
    ],
)
udf_layout = ValueParamItem(
    "layout",
    is_true=lambda layout, **kwargs: isinstance(layout, dict) and layout.get("layout"),
    function=lambda layout, **kwargs: layout["layout"],
)

udf_eikon_approach_fields = ValueParamItem(
    "fields",
    function=lambda fields, **kwargs: [{"name": i.upper()} for i in fields],
)


class DataGridRequestFactory(RequestFactory):
    def get_request_method(self, **kwargs) -> RequestMethod:
        return RequestMethod.POST


class DataGridRDPRequestFactory(DataGridRequestFactory):
    @cached_property
    def body_params_config(self):
        return rdp_universe, rdp_fields, parameters, rdp_layout


class DataGridUDFRequestFactory(DataGridRequestFactory):
    def create(self, session, *args, **kwargs):
        url_root = session._get_rdp_url_root()
        url = url_root.replace("rdp", "udf")

        method = self.get_request_method(**kwargs)
        header_parameters = kwargs.get("header_parameters") or {}
        extended_params = kwargs.get("extended_params") or {}
        body_parameters = self.get_body_parameters(*args, **kwargs)
        body_parameters = self.extend_body_parameters(body_parameters, extended_params)

        headers = {"Content-Type": "application/json"}
        headers.update(header_parameters)

        request = Request(
            url=url,
            method=method,
            headers=headers,
            json={
                "Entity": {
                    "E": "DataGrid_StandardAsync",
                    "W": {"requests": [body_parameters]},
                }
            },
        )
        closure = kwargs.get("closure")
        if closure:
            request.closure = closure
        return request

    @cached_property
    def body_params_config(self):
        return udf_universe, udf_fields, parameters, udf_layout

    def get_body_parameters(self, *args, **kwargs) -> dict:
        ticket = kwargs.get("ticket")
        if ticket:
            return {"ticket": ticket}

        return super().get_body_parameters(*args, **kwargs)


class DataGridUDFRequestFactoryEikonApproach(DataGridUDFRequestFactory):
    @cached_property
    def body_params_config(self):
        return udf_universe, udf_eikon_approach_fields, parameters, udf_layout
