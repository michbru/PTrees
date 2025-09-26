from enum import unique

from lseg.data._base_enum import StrEnum


@unique
class ShiftType(StrEnum):
    ADDITIVE = "Additive"
    RELATIVE = "Relative"
    RELATIVE_PERCENT = "RelativePercent"
    SCALED = "Scaled"
