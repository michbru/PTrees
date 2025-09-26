from enum import unique

from lseg.data._base_enum import StrEnum


@unique
class ArrayMainConstituentAssetClass(StrEnum):
    DEPOSIT = "Deposit"
    FUTURES = "Futures"
    SWAP = "Swap"
