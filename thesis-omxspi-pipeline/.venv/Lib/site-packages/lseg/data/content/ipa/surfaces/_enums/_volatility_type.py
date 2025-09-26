from enum import unique

from ....._base_enum import StrEnum


@unique
class VolatilityType(StrEnum):
    LOG_NORMAL_VOLATILITY = "LogNormalVolatility"
    NORMAL_VOLATILITY = "NormalVolatility"
