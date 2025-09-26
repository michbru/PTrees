from ._content_validator import DataGridRDPContentValidator, DataGridUDFContentValidator
from ._request_factory import (
    DataGridRDPRequestFactory,
    DataGridUDFRequestFactory,
    DataGridUDFRequestFactoryEikonApproach,
)
from ._response_factory import DataGridRDPResponseFactory, DataGridUDFResponseFactory
from .._content_data_provider import ContentDataProvider
from ...delivery._data._data_provider import ValidatorContainer

data_grid_rdp_data_provider = ContentDataProvider(
    request=DataGridRDPRequestFactory(),
    response=DataGridRDPResponseFactory(),
    validator=ValidatorContainer(content_validator=DataGridRDPContentValidator()),
)

data_grid_udf_data_provider = ContentDataProvider(
    request=DataGridUDFRequestFactory(),
    response=DataGridUDFResponseFactory(),
    validator=ValidatorContainer(content_validator=DataGridUDFContentValidator()),
)

data_grid_udf_eikon_approach_data_provider = ContentDataProvider(
    request=DataGridUDFRequestFactoryEikonApproach(),
    response=DataGridUDFResponseFactory(),
    validator=ValidatorContainer(content_validator=DataGridUDFContentValidator()),
)
