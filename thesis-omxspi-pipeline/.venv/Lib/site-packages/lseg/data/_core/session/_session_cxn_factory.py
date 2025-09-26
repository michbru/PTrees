from typing import Union

from ._session import Session
from ._session_cxn_type import SessionCxnType
from .connection import (
    PlatformDataConnection,
    PlatformDataAndDeployedConnection,
    DesktopConnection,
    DeployedConnection,
)

cxn_class_by_type = {
    SessionCxnType.DEPLOYED: DeployedConnection,
    SessionCxnType.PLATFORM_DATA: PlatformDataConnection,
    SessionCxnType.PLATFORM_DATA_AND_DEPLOYED: PlatformDataAndDeployedConnection,
    SessionCxnType.DESKTOP: DesktopConnection,
}

SessionConnection = Union[
    DeployedConnection,
    PlatformDataConnection,
    PlatformDataAndDeployedConnection,
    DesktopConnection,
]

PlatformConnection = Union[PlatformDataConnection, PlatformDataAndDeployedConnection, DeployedConnection]


def get_session_cxn(session_cxn_type: SessionCxnType, session: "Session") -> SessionConnection:
    cxn_class = cxn_class_by_type.get(session_cxn_type)

    if not cxn_class:
        raise ValueError(f"Can't find cxn_class by session_cxn_type: {session_cxn_type}")

    cxn = cxn_class(session)
    return cxn
