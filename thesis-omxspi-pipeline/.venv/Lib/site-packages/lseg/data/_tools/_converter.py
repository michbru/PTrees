from collections.abc import Iterable
from typing import List, Any, Union


def try_copy_to_list(obj: Any) -> Union[List[Any], Any]:
    if isinstance(obj, (list, tuple, set, dict)) and not isinstance(obj, str):
        return list(obj)

    return obj


class Copier:
    @staticmethod
    def get_list(obj: Any) -> Union[List[Any], Any]:
        if isinstance(obj, Iterable) and not isinstance(obj, str):
            return list(obj)

        return [obj]
