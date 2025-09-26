from enum import unique, Enum, auto


@unique
class LayerType(Enum):
    ACCESS_GET_DATA = auto()
    ACCESS_GET_HISTORY = auto()
    CONTENT = auto()
    CONTENT_FUND_AND_REF = auto()
    DELIVERY = auto()
