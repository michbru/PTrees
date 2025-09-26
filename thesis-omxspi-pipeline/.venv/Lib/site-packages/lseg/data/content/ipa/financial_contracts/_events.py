from functools import partialmethod

from ....delivery._stream import StreamEvt
from ....delivery._stream.events import PrvRDPStreamEvts


def dispatch(self: PrvRDPStreamEvts, ev: StreamEvt, message: dict):
    self.dispatch(ev, self.originator.data, self.originator.column_names, self.originator.owner)


class QuantitativeStreamEvts(PrvRDPStreamEvts):
    """
    Events from QuantitativeDataStream for User
    """

    dispatch_response = partialmethod(dispatch, StreamEvt.RESPONSE)
    dispatch_update = partialmethod(dispatch, StreamEvt.UPDATE)

    def dispatch_alarm(self, message: dict):
        self.dispatch(StreamEvt.ALARM, message.get("state"), self.originator.owner)

    def dispatch_ack(self, message: dict):
        self.dispatch(StreamEvt.ACK, message.get("state"), self.originator)
