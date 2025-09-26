from dataclasses import dataclass
from typing import TYPE_CHECKING, List, TypeVar, Generic, Any, Union

from ._endpoint_data import Error
from ..._tools import cached_property

if TYPE_CHECKING:
    from ._data_factory import BaseDataFactory
    import httpx

TypeData = TypeVar("TypeData")


@dataclass
class Response(Generic[TypeData]):
    is_success: bool
    raw: Union[List["httpx.Response"], "httpx.Response"]
    errors: List[Error]
    closure: Union[str, None]
    requests_count: int
    _data_factory: "BaseDataFactory"
    _kwargs: dict
    _data_raw: Any

    @cached_property
    def data(self) -> TypeData:
        return self._data_factory.create_data(self._data_raw, owner_=self, **self._kwargs)


def create_response(responses: List[Response], data_factory: "BaseDataFactory", kwargs: dict) -> Response:
    from ._response_factory import get_closure

    data_raw_items = []
    response_raw_items = []
    errors = []
    is_success = False
    closure = None
    once = False

    for response in responses:
        is_success = is_success or response.is_success
        data_raw_items.append(response.data.raw)

        if response.errors:
            errors += response.errors

        raw_response = response.raw
        response_raw_items.append(raw_response)

        if not once:
            closure = get_closure(raw_response[0] if isinstance(raw_response, list) else raw_response)
            once = True

    return Response(
        is_success,
        response_raw_items,
        errors,
        closure=closure,
        requests_count=len(responses),
        _data_factory=data_factory,
        _kwargs=kwargs,
        _data_raw=data_raw_items,
    )
