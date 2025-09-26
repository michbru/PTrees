from typing import TYPE_CHECKING, Union, Any

from ._session import Session
from ._session_cxn_type import SessionCxnType
from ._session_type import SessionType
from .event_code import EventCode
from ..._errors import ScopeError
from ..._tools import urljoin, cached_property, parse_url, fill

if TYPE_CHECKING:
    import httpx
    from .auth import GrantType
    from ...delivery._data import Request
    from ._session_cxn_factory import PlatformConnection


class PlatformSession(Session):
    """
    This class is designed for handling the session to Data Platform
    or Deployed Platform (TREP)
    - Data Platform are including handling an authentication and
        a token management (including refreshing token),
        also handling a real-time service discovery to get
        the service websocket endpoint and initialize the login for streaming
    - Deployed Platform is including the login for streaming
    """

    type = SessionType.PLATFORM

    def __init__(
        self,
        app_key=None,
        grant: "GrantType" = None,
        signon_control: bool = False,
        deployed_platform_host=None,
        deployed_platform_username=None,
        dacs_position=None,
        dacs_application_id=None,
        on_state=None,
        on_event=None,
        name="default",
        auto_reconnect=None,
        server_mode: bool = None,
        base_url=None,
        auth_url=None,
        auth_authorize=None,
        auth_token=None,
        realtime_distribution_system_url=None,
        revoke_url=None,
        proxies: Union[str, dict] = None,
        app_name: str = None,
    ):
        super().__init__(
            app_key,
            on_state=on_state,
            on_event=on_event,
            deployed_platform_username=deployed_platform_username,
            dacs_position=dacs_position,
            dacs_application_id=dacs_application_id,
            name=name,
            proxies=proxies,
            app_name=app_name,
        )

        self._grant = grant
        self._take_signon_control = signon_control

        self._auto_reconnect = auto_reconnect
        self._server_mode = server_mode
        self._base_url = base_url
        self._auth_url = auth_url
        self._revoke_url = revoke_url
        self._auth_authorize = auth_authorize
        self._auth_token = auth_token
        self._realtime_dist_system_url = realtime_distribution_system_url

        self._enable_scope_verification = self.config.get(f"sessions.platform.{name}.verify_scope", True)

        self._deployed_platform_host = deployed_platform_host
        self._deployed_platform_connection_name = self.name

        is_debug = self._is_debug()
        if self._deployed_platform_host is None and self._realtime_dist_system_url:
            parse_result = parse_url(self._realtime_dist_system_url)
            self._deployed_platform_host = parse_result.netloc
            is_debug and self.debug(
                f"Using the Refinitiv realtime distribution system : "
                f"url at {self._realtime_dist_system_url},\n"
                f"deployed_platform_host={self._deployed_platform_host}"
            )

        elif self._deployed_platform_host and not self._realtime_dist_system_url:
            is_debug and self.debug(f"Using the specific deployed_platform_host={self._deployed_platform_host}")

        elif self._deployed_platform_host and self._realtime_dist_system_url:
            # what to do ?
            pass

    @property
    def stream_auto_reconnection(self):
        return self._auto_reconnect

    @property
    def server_mode(self) -> bool:
        return self._server_mode

    @property
    def signon_control(self):
        return self._take_signon_control

    @property
    def authentication_token_endpoint_url(self) -> str:
        return urljoin(self._get_rdp_url_root() or "", self._auth_url or "", self._auth_token or "")

    @property
    def _token_revoke_url(self):
        return urljoin(self._get_rdp_url_root() or "", self._revoke_url or "")

    def _cxns_stop_auto_reconnect(self, _):
        from ...delivery._stream import get_cxn_cfg_provider

        cxn_cfg_provider = get_cxn_cfg_provider(self)
        cxn_cfg_provider.wait_start_connecting()

        from ...delivery._stream import stream_cxn_cache

        if stream_cxn_cache.has_cxns(self):
            cxns_by_session = stream_cxn_cache.get_cxns(self)
            for cxn in cxns_by_session:
                cxn.wait_start_connecting()

    def _on_authentication_success(self, message):
        from ...delivery._stream import get_cxn_cfg_provider

        cxn_cfg_provider = get_cxn_cfg_provider(self)
        cxn_cfg_provider.start_connecting()

        from ...delivery._stream import stream_cxn_cache

        if stream_cxn_cache.has_cxns(self):
            cxns_by_session = stream_cxn_cache.get_cxns(self)
            for cxn in cxns_by_session:
                cxn.start_connecting()

        self._call_on_event(EventCode.SessionAuthenticationSuccess, message)

    @cached_property
    def _connection(self) -> "PlatformConnection":
        from ._session_cxn_factory import get_session_cxn

        cxn_type = self._get_session_cxn_type()
        cxn = get_session_cxn(cxn_type, self)

        if cxn_type in [SessionCxnType.PLATFORM_DATA, SessionCxnType.PLATFORM_DATA_AND_DEPLOYED]:
            from .event import UpdateEvent

            auth_mgr = cxn.auth_manager
            auth_mgr.on(UpdateEvent.AUTHENTICATION_SUCCESS, self._on_authentication_success)
            auth_mgr.on(
                UpdateEvent.AUTHENTICATION_FAILED,
                lambda message: self._call_on_event(EventCode.SessionAuthenticationFailed, message),
            )
            auth_mgr.on(
                UpdateEvent.RECONNECTING,
                lambda message: self._call_on_event(EventCode.SessionReconnecting, "Session is reconnecting"),
            )
            auth_mgr.on(UpdateEvent.UPDATE_ACCESS_TOKEN, self.update_access_token)
            auth_mgr.on(UpdateEvent.REFRESH_TOKEN_EXPIRED, self._cxns_stop_auto_reconnect)
            auth_mgr.on(UpdateEvent.CLOSE_AUTH_MANAGER, self._cxns_stop_auto_reconnect)

        self._is_debug() and self.debug(f"Created session connection {cxn_type}")
        return cxn

    def _get_session_cxn_type(self) -> SessionCxnType:
        if self._grant and self._grant.is_valid() and self._deployed_platform_host:
            cxn_type = SessionCxnType.PLATFORM_DATA_AND_DEPLOYED

        elif self._grant and self._grant.is_valid():
            cxn_type = SessionCxnType.PLATFORM_DATA

        elif self._deployed_platform_host:
            cxn_type = SessionCxnType.DEPLOYED

        else:
            raise AttributeError("Can't get a session connection type")

        return cxn_type

    def _get_rdp_url_root(self):
        return self._base_url

    def _get_auth_token_uri(self):
        auth_token_uri = urljoin(self._auth_url, self._auth_token)
        return urljoin(self._get_rdp_url_root(), auth_token_uri)

    async def http_request_async(self, request: "Request") -> "httpx.Response":
        return await self._connection.http_request_async(request)

    def http_request(self, request: "Request") -> "httpx.Response":
        return self._connection.http_request(request)

    def __str__(self) -> str:
        template = "\t\t{} = {}"

        description = [
            self.classname,
            fill(
                name=self.name,
                connection=self._connection,
                stream_auto_reconnection=self.stream_auto_reconnection,
                template=template,
                delim="\n",
            ),
        ]

        cnx_type = self._get_session_cxn_type()
        if cnx_type in {SessionCxnType.PLATFORM_DATA, SessionCxnType.PLATFORM_DATA_AND_DEPLOYED}:
            description.append(
                fill(
                    authentication_token_endpoint_url=self.authentication_token_endpoint_url,
                    signon_control=self.signon_control,
                    server_mode=self.server_mode,
                    template=template,
                    delim="\n",
                )
            )

        if cnx_type in {SessionCxnType.PLATFORM_DATA_AND_DEPLOYED, SessionCxnType.DEPLOYED}:
            description.append(
                fill(
                    deployed_server=self._deployed_platform_host,
                    dacs_username=self._dacs_params.deployed_platform_username,
                    dacs_position=self._dacs_params.dacs_position,
                    dacs_application_id=self._dacs_params.dacs_application_id,
                    template=template,
                    delim="\n",
                )
            )

        description.append(
            fill(
                state=self._state,
                session_id=self.session_id,
                logger_name=self._logger.name,
                delim="\n",
                template=template,
            )
        )

        return "\n".join(description)

    def verify_scope(self, key: str, method: str):
        if self._enable_scope_verification:
            self._connection.auth_manager.verify_scope(key, method)

    def _handle_insufficient_scope(self, path: str, method: str, message: str) -> None:
        try:
            required_scopes_str, missing_scopes_str = (
                message.lstrip("access denied. Scopes required to access the resource: ")
                .replace("[", "")
                .replace("]", "")
                .split(". Missing scopes: ")
            )
            required_scope_groups = required_scopes_str.split(" or ")
        except (AttributeError, ValueError) as e:
            self.warning(f"{e}. Unable to parse scope error message: {message}")
            return
        required_scopes = [set(i.split()) for i in required_scope_groups]
        self._connection.auth_manager.set_scope(path, method, required_scopes)
        raise ScopeError(
            required_scopes,
            self._connection.auth_manager._token_info.scope,
            path,
            method,
        )

    def __eq__(self, other: Any):
        if not isinstance(self, PlatformSession):
            return False
        return self._grant == other._grant and self._base_url == other._base_url

    def __hash__(self):
        return super().__hash__()
