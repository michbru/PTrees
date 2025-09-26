import abc
from itertools import product
from typing import List, Dict, Tuple, Union

import pandas as pd

from .._tools import convert_dtypes, convert_str_to_timestamp
from .._types import Strings


class WrappedList:
    def __init__(self) -> None:
        self._list = []

    def __iter__(self):
        return iter(self._list)

    def __getitem__(self, item):
        return self._list[item]


class ListOfColumns(WrappedList, abc.ABC):
    last_columns: List[str]

    def append(self, inst_name: str, columns: List[str]) -> None:
        self.last_columns = columns
        self._do_append(inst_name, columns)

    def _do_append(self, inst_name: str, columns: List[str]) -> None:
        raise NotImplementedError()

    def insert(self, idx: int, inst_name: str, columns: List[str]) -> None:
        raise NotImplementedError()

    def flatten(self) -> List[str]:
        return [col for subcolumns in self for col in subcolumns]

    def get_instidx_by_num_columns_from_left(self, num: int) -> Dict[int, int]:
        # {0: 0, 1: 1}
        instidx_by_num_columns_from_left = {}
        for instidx in range(num):
            instidx_by_num_columns_from_left[instidx] = sum([len(subcols) for subcols in self[:instidx]])
        return instidx_by_num_columns_from_left


class ListOfColumnsOneHeader(ListOfColumns):
    """
    Examples
    --------
    >>> _list
    ... [
    ...     ['EUR='],
    ...     ['GBP=']
    ... ]

    """

    _list: List[List[str]]

    def _do_append(self, inst_name: str, _: List[str]) -> None:
        self._list.append([inst_name])

    def insert(self, idx: int, inst_name: str, _: List[str]) -> None:
        self._list.insert(idx, [inst_name])


class ListOfColumnsHeaders(ListOfColumns):
    """
    Examples
    --------
    >>> _list
    ... [
    ...     [('EUR=', 'EVENT_TYPE'), ('EUR=', 'BID'), ('EUR=', 'ASK')],
    ...     [('GBP=', 'EVENT_TYPE'), ('GBP=', 'BID'), ('GBP=', 'ASK')]
    ... ]
    """

    _list: List[List[Tuple[str, str]]]

    def _do_append(self, inst_name: str, columns: List[str]) -> None:
        self._list.append(list(product([inst_name], columns)))

    def insert(self, idx: int, inst_name: str, columns: List[str]) -> None:
        self._list.insert(idx, list(product([inst_name], columns)))


def create_listofcolumns(num_headers: int) -> ListOfColumns:
    if num_headers == 1:
        return ListOfColumnsOneHeader()
    return ListOfColumnsHeaders()


class BadRaws(WrappedList):
    def append(self, raw: Union[dict, list], universe: Strings, instidx: int) -> bool:
        # it means error in response for custom instruments
        if not raw:
            raw = {"universe": {"ric": universe[instidx]}}

        # it means error in response for historical pricing
        elif isinstance(raw, list):
            raw = raw[0]

        # it means in response for historical pricing events
        elif isinstance(raw, dict) and not raw.get("headers"):
            raw = {"universe": {"ric": universe[instidx]}}

        else:
            return False

        self._list.append((instidx, raw))
        return True

    def insert_to(self, l: ListOfColumns) -> None:
        columns = l.last_columns or "Field"
        insert = l.insert
        for idx, bad_raw in self:
            insert(idx, bad_raw["universe"]["ric"], columns)


class Columns(abc.ABC):
    def __init__(self, raw_columns: Union[List[str], List[Tuple[str, str]]]) -> None:
        self._raw_columns = raw_columns

    @property
    def len(self) -> int:
        return len(self._raw_columns)

    def as_pd_object(self, headers: List[str], use_multiindex: bool) -> pd.Index:
        raise NotImplementedError()


class ColumnsOneHeader(Columns):
    """
    Examples
    --------
    >>> _raw_columns
    ... ["S)MyUSD.GESG1-150112"]
    """

    _raw_columns: List[str]

    def as_pd_object(self, headers: List[str], use_multiindex: bool) -> pd.Index:
        """
        Examples
        --------
        >>> columns = ColumnsOneHeader(["S)MyUSD.GESG1-150112"])
        >>> columns.as_pd_object(["TRDPRC_1"], use_multiindex=False)
        ... pd.Index(["S)MyUSD.GESG1-150112"], dtype="object", name="TRDPRC_1")
        >>> columns.as_pd_object(["TRDPRC_1"], use_multiindex=True)
        ... pd.MultiIndex([("S)MyUSD.GESG1-150112", "TRDPRC_1")])
        """
        if use_multiindex:
            pd_object = pd.MultiIndex.from_tuples(tuples=product(self._raw_columns, headers))
        else:
            pd_object = pd.Index(data=self._raw_columns, name=headers[0])
        return pd_object


class ColumnsHeaders(Columns):
    """
    Examples
    --------
    >>> _raw_columns
    ... [
    ...     ("IBM.N", "TRDPRC_1"),
    ...     ("IBM.N", "HIGH_1"),
    ...     ("IBM.N", "LOW_1"),
    ...     ("EUR=", "BID"),
    ...     ("EUR=", "ASK"),
    ... ]
    """

    _raw_columns: List[Tuple[str, str]]

    def as_pd_object(self, headers: List[str], use_multiindex: bool) -> pd.Index:
        """
        Examples
        --------
        >>> columns = ColumnsHeaders([("IBM.N", "TRDPRC_1"), ("IBM.N", "HIGH_1"), ("IBM.N", "LOW_1"), ("EUR=", "BID"), ("EUR=", "ASK")])
        >>> columns.as_pd_object(["BID", "ASK", "BID_HIGH_1", "BID_LOW_1"], use_multiindex=False|True)
        ... pd.MultiIndex([("IBM.N", "TRDPRC_1"), ("IBM.N", "HIGH_1"), ("IBM.N", "LOW_1"), ("EUR=", "BID"), ("EUR=", "ASK"))
        """
        return pd.MultiIndex.from_tuples(tuples=self._raw_columns)


def create_columns(num_headers: int, raw_columns: List[str]) -> Columns:
    if num_headers == 1:
        return ColumnsOneHeader(raw_columns)
    return ColumnsHeaders(raw_columns)


def sort_columns(upper_fields: List[str]) -> callable:
    def sort_key(obj: Tuple[int, str]) -> int:
        _, column = obj
        try:
            return upper_fields.index(column.upper())
        except (ValueError, AttributeError):
            return 0

    return sort_key


class HPHeaders(list):
    def __init__(self, headers: List[dict]) -> None:
        super().__init__()
        names = []
        timestamp_date_idx = None
        for idx, hdr in enumerate(headers):
            header_name = hdr["name"]
            if header_name in {"DATE_TIME", "DATE"}:
                timestamp_date_idx = idx
                continue

            names.append(header_name)
            self.append(hdr)

        self.names = names
        self.timestamp_date_idx = timestamp_date_idx


class HPItem:
    def __init__(self, raw: Union[dict, list]) -> None:
        super().__init__()
        try:
            self.ric = raw["universe"]["ric"]
            self.data = raw["data"]
            self.headers = HPHeaders(raw["headers"])
        except TypeError:
            self.ric = ""
            self.data = []
            self.headers = HPHeaders([])

    def __bool__(self) -> bool:
        return bool(self.data)

    def __iter__(self):
        return iter(self.data)


def get_idx(idxs: List[int]) -> callable:
    def sort_key(obj: Tuple[int, object]):
        return idxs.index(obj[0])

    return sort_key


def sort_by_order(l: List, new_order: List[int]) -> List:
    return [item for _, item in sorted(enumerate(l), key=get_idx(new_order))]


class NotNoneList(list):
    def __init__(self, l: list) -> None:
        super().__init__()
        for obj in l:
            self.append(obj)

    def append(self, obj) -> None:
        super().append(pd.NA if obj is None else obj)


class ItemsByDate(dict):
    def append(
        self, timestamp_date_idx: int, instidx: int, unsorted_l: list, columns: List[str], new_order: List[int]
    ) -> None:
        unsorted_l = NotNoneList(unsorted_l)  # copy
        date = convert_str_to_timestamp(unsorted_l.pop(timestamp_date_idx))
        self.setdefault(date, []).append((instidx, sort_by_order(unsorted_l, new_order), columns))

    def process_data(
        self, num_raws: int, listofcolumns: ListOfColumns, use_multiindex: bool
    ) -> Tuple[list, pd.Index, list]:
        instidx_by_num_columns_from_left = listofcolumns.get_instidx_by_num_columns_from_left(num_raws)
        last_columns = listofcolumns.last_columns
        columns = create_columns(len(last_columns), listofcolumns.flatten())
        num_columns = columns.len

        data = []
        index = []
        data_append = data.append
        index_append = index.append

        for date, items in self.items():
            prev_idx = None
            counter = 0
            template = [pd.NA] * num_columns
            for instidx, raw_data, raw_columns in items:
                if (counter != 0 and counter % num_raws == 0) or prev_idx == instidx:
                    index_append(date)
                    data_append(template)
                    template = [pd.NA] * num_columns
                    prev_idx = instidx

                if prev_idx is None:
                    prev_idx = instidx

                counter += 1

                left_idx = instidx_by_num_columns_from_left[instidx]
                right_idx = left_idx + len(raw_columns)
                for item, i in zip(raw_data, range(left_idx, right_idx)):
                    template[i] = item

            index_append(date)
            data_append(template)

        return data, columns.as_pd_object(last_columns, use_multiindex), index


class HistoricalBuilder:
    def build_one(self, raw: dict, fields: Strings, axis_name: str, **_) -> pd.DataFrame:
        """
        Build DataFrame from raw data for one instrument.

        Examples:
        --------
        >>> raw
        ... {
        ...     "universe": {"ric": "GS.N"},
        ...     "interval": "P1D",
        ...     "summaryTimestampLabel": "endPeriod",
        ...     "adjustments": ["exchangeCorrection", "manualCorrection", "CCH", "CRE", "RTS", "RPO"],
        ...     "defaultPricingField": "TRDPRC_1",
        ...     "qos": {"timeliness": "delayed"},
        ...     "headers": [{"name": "DATE", "type": "string"},
        ...                 {"name": "BID", "type": "number", "decimalChar": "."},
        ...                 {"name": "ASK", "type": "number", "decimalChar": "."}],
        ...     "data": [["2023-08-21", 322.08, 322.15],
        ...              ["2023-08-16", 329.03, 329.04],
        ...              ["2023-08-15", 332.37, 332.47]],
        ...     "meta": {
        ...         "blendingEntry": {
        ...             "headers": [{"name": "DATE", "type": "string"},
        ...                         {"name": "BID", "type": "number", "decimalChar": "."},
        ...                         {"name": "ASK", "type": "number", "decimalChar": "."}],
        ...             "data": [["2023-08-21", 322.08, 322.15]]}
        ...     }
        ... }
        """

        hp_item = HPItem(raw)

        if not hp_item:
            return pd.DataFrame()

        upper_fields = [f.upper() for f in fields]

        columns = []
        new_order = []
        for idx, column in sorted(enumerate(hp_item.headers.names), key=sort_columns(upper_fields)):
            columns.append(column)
            new_order.append(idx)

        data = []
        index = []
        timestamp_date_idx = hp_item.headers.timestamp_date_idx
        for unsorted_l in hp_item:
            unsorted_l = NotNoneList(unsorted_l)  # copy
            index.append(convert_str_to_timestamp(unsorted_l.pop(timestamp_date_idx)))
            data.append(sort_by_order(unsorted_l, new_order))

        columns = pd.Index(data=columns, name=hp_item.ric)
        index = pd.Index(data=index, name=axis_name)
        df = pd.DataFrame(data=data, columns=columns, index=index)
        df = convert_dtypes(df)
        df.sort_index(inplace=True)
        return df

    def build(
        self, raws: List[dict], universe: Strings, fields: Strings, axis_name: str, use_multiindex: bool = False, **_
    ) -> pd.DataFrame:
        listofcolumns = None
        bad_raws = BadRaws()
        items_by_date = ItemsByDate()
        upper_fields = [f.upper() for f in fields]
        for instidx, raw in enumerate(raws):
            if bad_raws.append(raw, universe, instidx):
                continue

            hp_item = HPItem(raw)

            columns = []
            new_order = []
            for idx, column in sorted(enumerate(hp_item.headers.names), key=sort_columns(upper_fields)):
                columns.append(column)
                new_order.append(idx)

            timestamp_date_idx = hp_item.headers.timestamp_date_idx
            for unsorted_l in hp_item:
                items_by_date.append(timestamp_date_idx, instidx, unsorted_l, columns, new_order)

            if listofcolumns is None:
                listofcolumns = create_listofcolumns(len(columns))

            listofcolumns.append(hp_item.ric, columns)

        if not items_by_date:
            return pd.DataFrame()

        bad_raws.insert_to(listofcolumns)

        data, columns, index = items_by_date.process_data(len(raws), listofcolumns, use_multiindex)

        index = pd.Index(data=index, name=axis_name)
        df = pd.DataFrame(data=data, columns=columns, index=index)
        df = convert_dtypes(df)
        df.sort_index(inplace=True)
        return df


historical_builder = HistoricalBuilder()
custom_insts_builder = historical_builder
