from typing import TYPE_CHECKING

from ._listeners import OMMListenersUniverseStm
from ._record import UniverseRecord
from .._tools import cached_property
from ..delivery._stream import PrvOMMStream, get_service_and_details_omm
from ..delivery._stream.events import PrvOMMStreamEvts

if TYPE_CHECKING:
    from ._universe_streams import _UniverseStreams
    from .._types import ExtendedParams
    from .._content_type import ContentType
    from .._core.session import Session


class _UniverseStream(PrvOMMStream):
    record_class = UniverseRecord

    def __init__(
        self,
        content_type: "ContentType",
        name: str,
        session: "Session",
        owner: "_UniverseStreams",
        fields: list = None,
        service: str = None,
        api: str = None,
        extended_params: "ExtendedParams" = None,
    ):
        if name is None:
            raise AttributeError("Instrument name must be defined.")

        stream_id = session._get_omm_stream_id()
        self.classname: str = f"{self.__class__.__name__} owner.id={owner.id} id={stream_id} name='{name}'"  # should be before PrvOMMStream.__init__
        service, details = get_service_and_details_omm(content_type, session, service, api)
        self.record: UniverseRecord = self.record_class(fields)
        PrvOMMStream.__init__(
            self,
            stream_id=stream_id,
            session=session,
            name=name,
            details=details,
            domain="MarketPrice",
            service=service,
            fields=fields,
            extended_params=extended_params,
        )
        self.owner = owner

    def keys(self):
        return self.record.get_fields_keys()

    def values(self):
        return self.record.get_fields_values()

    def items(self):
        return self.record.get_fields_items()

    def __iter__(self):
        return self.record.__iter__()

    def __getitem__(self, field):
        return self.record.__getitem__(field)

    def __len__(self):
        return len(self.fields) if self.fields else 0

    def __repr__(self):
        return str({"name": self.name, "service": self.service, "fields": self.record.get_fields()})

    def __str__(self):
        service_name = f"{self.service or 'Unknown service'}|{self.name}"
        field_value = ",".join(f"{f}:{v}" for f, v in self.record.get_fields())
        return f"{service_name}[{field_value}]"

    @cached_property
    def events(self) -> PrvOMMStreamEvts:
        return PrvOMMStreamEvts(self)

    @cached_property
    def cxn_listeners(self) -> OMMListenersUniverseStm:
        return OMMListenersUniverseStm(self)
