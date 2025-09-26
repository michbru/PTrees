from typing import TYPE_CHECKING

from ._definition_base import BaseDefinition
from .._df_build_type import DFBuildType
from .._header_type import HeaderType
from ..._content_type import ContentType

if TYPE_CHECKING:
    from ..._types import OptDict, StrStrings


class EikonApproachDefinition(BaseDefinition):
    def __init__(self, universe: "StrStrings", fields: "StrStrings", parameters: "OptDict", header_type: HeaderType):
        super().__init__(ContentType.DATA_GRID_UDF_EIKON_APPROACH, universe, fields, header_type, parameters)

    def _update_content_type(self, session):
        self._kwargs["__dfbuild_type__"] = DFBuildType.INDEX
