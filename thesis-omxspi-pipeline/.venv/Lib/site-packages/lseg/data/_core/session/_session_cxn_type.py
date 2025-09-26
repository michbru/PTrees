from enum import Enum, auto


class SessionCxnType(Enum):
    DEPLOYED = auto()
    PLATFORM_DATA = auto()
    PLATFORM_DATA_AND_DEPLOYED = auto()
    DESKTOP = auto()
    NONE = auto()
