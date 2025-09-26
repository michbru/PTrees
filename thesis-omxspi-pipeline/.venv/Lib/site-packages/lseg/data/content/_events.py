from functools import partialmethod
from typing import TYPE_CHECKING

from ..delivery._stream import StreamEvt
from ..delivery._stream.events import PrvOMMStreamEvts

if TYPE_CHECKING:
    from ._universe_stream import _UniverseStream
    from ._universe_streams import _UniverseStreams  # noqa: F401


def dispatch(self: PrvOMMStreamEvts, ev: StreamEvt, message: dict, universe_stream: "_UniverseStream"):
    self.dispatch(ev, message, universe_stream.name, self.originator.owner)


class _UniverseStreamsEvts(PrvOMMStreamEvts):
    """
    Events from _UniverseStreams for User
    """

    dispatch_refresh = partialmethod(dispatch, StreamEvt.REFRESH)
    dispatch_status = partialmethod(dispatch, StreamEvt.STATUS)
    dispatch_complete = partialmethod(PrvOMMStreamEvts._dispatch_owner, StreamEvt.COMPLETE)
    dispatch_error = partialmethod(dispatch, StreamEvt.ERROR)
    dispatch_update = partialmethod(dispatch, StreamEvt.UPDATE)
    dispatch_ack = partialmethod(dispatch, StreamEvt.ACK)
