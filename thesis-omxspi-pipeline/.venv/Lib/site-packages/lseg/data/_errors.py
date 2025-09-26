from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:
    from .delivery._data._data_provider import Response


class LDError(Exception):
    """Base class for exceptions in this lseg-data module.

    Parameters
    ----------
    code: int
        error code for this exception
    message: str
        error description for this exception
    """

    response: "Response"

    def __init__(self, code: int = None, message: str = None):
        self.code = code
        self.message = message

    def __str__(self) -> str:
        if self.code:
            output = f"Error code {self.code} | {self.message}"
        else:
            output = f"{self.message}"

        return output


class SessionError(LDError):
    pass


class StreamingError(LDError):
    pass


class StreamConnectionError(LDError):
    pass


class PlatformSessionError(SessionError):
    pass


class DesktopSessionError(SessionError):
    pass


class ESGError(LDError):
    pass


class NewsHeadlinesError(LDError):
    pass


class EndpointError(LDError):
    pass


class StreamError(LDError):
    pass


class StreamingPricesError(LDError):
    pass


class ItemWasNotRequested(LDError):
    def __init__(self, item_type, not_requested, requested):
        item_type = f"{item_type}{'s' if len(not_requested) > 1 else ''}"
        super().__init__(message=f"{item_type} {not_requested} was not requested : {requested}")


class EnvError(LDError):
    pass


class BondPricingError(LDError):
    pass


class FinancialContractsError(LDError):
    pass


class RequiredError(LDError):
    pass


class ConfigurationError(LDError):
    pass


class ScopeError(LDError):
    def __init__(
        self,
        required_scope: List[Set[str]],
        available_scope: Set[str],
        key: str,
        method: str,
    ):
        missing_scopes = [scope - available_scope for scope in required_scope]
        self.required_scope = required_scope
        self.available_scope = available_scope
        self.key = key
        self.method = method
        self.missing_scopes = missing_scopes
        super().__init__(
            message=f"Insufficient scope for key={key}, method={method}.\n"
            f"Required scopes: {' OR '.join(map(str, required_scope))}\n"
            f"Available scopes: {available_scope or '{}'}\n"
            f"Missing scopes: {' OR '.join(map(str, missing_scopes))}",
        )
