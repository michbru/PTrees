from enum import unique

from ....._base_enum import StrEnum


@unique
class MoneynessType(StrEnum):
    FWD = "Fwd"
    SIGMA = "Sigma"
    SPOT = "Spot"
