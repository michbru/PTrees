from collections import defaultdict
from typing import TYPE_CHECKING, Union, List, Tuple, Dict

from pandas import DataFrame

from ._containers import FieldsContainer
from ._intervals_consts import NON_INTRA_DAY_INTERVALS
from .._adc_headers import create_adc_headers_al_get_history
from .._log import is_debug
from .._tools import ohlc, convert_dtypes, convert_str_to_timestamp
from ..content._df_builder import get_adc_dfbuilder
from ..content._historical_df_builder import sort_by_order, HPItem

if TYPE_CHECKING:
    from .context_collection import GetHistoryCustInstContext, HPContext, GetHistoryADCContextType
    from .._adc_headers._headers import HeadersALGetHistory
    from logging import Logger


def merged(source: list, target: list, skip: tuple) -> bool:
    items_source = set(idx for idx, item in enumerate(source) if item is not object and idx not in skip)

    if not items_source:
        return False

    free_places_target = set(idx for idx, item in enumerate(target) if item is object and idx not in skip)

    if not free_places_target:
        return False

    intersection = free_places_target.intersection(items_source)
    if not intersection or intersection != items_source:
        return False

    for idx in items_source:
        target[idx] = source[idx]

    return True


def sort_headers(upper_fields: List[str]) -> callable:
    def sort_key(obj: Tuple[int, dict]) -> int:
        _, header = obj
        try:
            field = header.get("field") or header.get("name")
            return upper_fields.index(field.upper())
        except (ValueError, AttributeError):
            return 0

    return sort_key


def fill_list(target: list, source: list):
    source_idxs = range(len(source) - 1, -1, -1)
    target_idxs = range(len(target) - 1, -1, -1)
    for source_idx, target_idx in zip(source_idxs, target_idxs):
        target[target_idx] = source[source_idx]


def is_same_list(a: list) -> callable:
    def filter_key(b: list) -> bool:
        return a == b

    return filter_key


class UniqueListOfLists(list):
    def __init__(self, ll: List[list] = None) -> None:
        super().__init__()
        ll = ll or []
        for l in ll:
            self.append(l)

    def append(self, l: list):
        if not self.has(l):
            super().append(l)

    def has(self, l: list) -> bool:
        return any(filter(is_same_list(l), self))

    def get_lists_by_inst(self, date_idx: int, inst_idx: int) -> Dict[str, list]:
        lists_by_inst = defaultdict(list)
        skip = (date_idx, inst_idx)
        for l in self:
            date = l[date_idx]
            if not date:
                continue

            timestamp = convert_str_to_timestamp(date)
            lists = lists_by_inst[l[inst_idx]]

            is_merged = False
            for cache in lists:
                cache_timestamp = cache[date_idx]
                if cache_timestamp != timestamp:
                    continue

                is_merged = merged(l, cache, skip)
                if is_merged:
                    break

            if not is_merged:
                l[date_idx] = timestamp
                lists.append(l)

        return lists_by_inst


def get_converter_hp_to_adc_list(hp_item: HPItem, adc_headers: "HeadersALGetHistory") -> callable:
    hp_date_idx = hp_item.headers.timestamp_date_idx
    ric = hp_item.ric
    len_headers = len(adc_headers)
    inst_idx = adc_headers.inst_idx
    date_idx = adc_headers.date_idx

    if hp_date_idx is not None:

        def converter_hp_to_adc_list(l_):
            l_ = list(l_)  # copy
            new_l = [object] * len_headers
            new_l[inst_idx] = ric
            new_l[date_idx] = l_.pop(hp_date_idx)
            fill_list(new_l, l_)
            return new_l

    else:

        def converter_hp_to_adc_list(l_):
            new_l = [object] * len_headers
            new_l[inst_idx] = ric
            fill_list(new_l, l_)
            return new_l

    return converter_hp_to_adc_list


def build_common_df_with_date_as_index(
    adc: "GetHistoryADCContextType",
    hp: "HPContext",
    cust_inst: "GetHistoryCustInstContext",
    fields: FieldsContainer,
    interval: Union[str, None],
) -> DataFrame:
    adc_headers = create_adc_headers_al_get_history(adc.data_grid_type, adc.raw)
    unsorted_adc_headers = adc_headers
    interim_data = UniqueListOfLists()
    hp_headers = None
    for hp_raw_item in hp.raw:
        hp_item = HPItem(hp_raw_item)
        if hp_item.headers and hp_headers is None:
            hp_headers = hp_item.headers
            len_hp_headers = len(hp_headers)
            for l in adc.raw["data"]:
                interim_data.append(l + [object] * len_hp_headers)

            unsorted_adc_headers = adc_headers + adc_headers.transform_hp_headers_to_adc(hp_headers)

        converter_hp_to_adc_list = get_converter_hp_to_adc_list(hp_item, adc_headers)

        for l in hp_item:
            interim_data.append(converter_hp_to_adc_list(l))

    common_headers = []
    new_order = []
    upper_fields = [f.upper() for f in fields]
    for idx, header in sorted(enumerate(unsorted_adc_headers), key=sort_headers(upper_fields)):
        common_headers.append(header)
        new_order.append(idx)

    lists_by_inst = interim_data.get_lists_by_inst(unsorted_adc_headers.date_idx, unsorted_adc_headers.inst_idx)

    common_data = []
    for lists in lists_by_inst.values():
        for unsorted_l in lists:
            common_data.append(sort_by_order(unsorted_l, new_order))

    has_cust_inst_raw = bool(cust_inst.raw)
    df = get_adc_dfbuilder(adc.data_grid_type).build_date_as_index(
        adc_headers.set_headers_to({"data": common_data}, common_headers),
        adc.header_type,
        use_multiindex=has_cust_inst_raw,
    )

    if has_cust_inst_raw:
        df = cust_inst.join_common_df(df)

    df = convert_dtypes(df)

    if interval is not None and interval not in NON_INTRA_DAY_INTERVALS:
        df.index.names = ["Timestamp"]

    return df


def build_df_date_as_index(
    adc: "GetHistoryADCContextType",
    hp: "HPContext",
    cust_inst: "GetHistoryCustInstContext",
    fields: FieldsContainer,
    interval: Union[str, None],
    logger: "Logger",
) -> DataFrame:
    is_debug_ = is_debug(logger)
    is_debug_ and logger.debug("[HistoryDFBuilder.build_df_date_as_index] Start")

    if adc.can_build_df:
        df = adc.build_df_with_date_as_index()

    elif hp.can_build_df:
        df = hp.build_df_with_date_as_index()

    elif cust_inst.can_join_hp_df:
        df = cust_inst.join_hp_df(hp.build_df_with_date_as_index())

    elif cust_inst.can_build_df:
        df = cust_inst.build_df_with_date_as_index()

    else:
        df = build_common_df_with_date_as_index(adc, hp, cust_inst, fields, interval)

    is_debug_ and logger.debug("[HistoryDFBuilder.build_df_date_as_index] End")

    if df is None:
        raise ValueError("build_config is not defined correctly")

    df.ohlc = ohlc.__get__(df, None)
    return df
