from __future__ import annotations
import time
from typing import Iterable, List


def chunks(lst: List[str], n: int) -> Iterable[List[str]]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def backoff_retry(fn, *, tries=5, base_sleep=1.0, exc_types=(Exception,)):
    """Simple exponential backoff wrapper."""
    def wrapper(*args, **kwargs):
        delay = base_sleep
        for attempt in range(tries):
            try:
                return fn(*args, **kwargs)
            except exc_types as e:
                if attempt == tries - 1:
                    raise
                time.sleep(delay)
                delay *= 2
    return wrapper
