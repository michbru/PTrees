from ..._errors import LDError


class TradefeedrError(LDError):
    """Base class for exceptions in this module."""

    pass


class PreTradeForecastInputSizeMismatch(TradefeedrError):
    pass
