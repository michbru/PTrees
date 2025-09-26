import dataclasses
from copy import deepcopy
from functools import partial
from itertools import product
from typing import List, Any, Dict, Union, Callable, TYPE_CHECKING

import pandas as pd

from ._df_build_type import DFBuildType
from ._header_type import HeaderType
from .fundamental_and_reference._data_grid_type import DataGridType
from .._adc_headers._headers_factory import make_create_adc_headers
from .._layer_type import LayerType
from .._tools import get_unique_list, convert_dtypes, convert_str_to_timestamp
from .._types import TimestampOrNaT

if TYPE_CHECKING:
    from .._adc_headers._headers import HeadersCLIndex, HeadersCLDateAsIndex


@dataclasses.dataclass
class CacheItem:
    """Data cache item."""

    fields_by_inst: Dict[str, List[Any]] = dataclasses.field(init=False, default_factory=dict)

    def add(self, inst: str, fields: List[Any]):
        """
        Add cache item as an instance:fields key-value pair.

        Parameters
        ----------
        inst : str
            Instance name.
        fields : List[Any]
            Instance fields.
        """
        self.fields_by_inst[inst] = fields

    def has(self, inst: str) -> bool:
        """
        Boolean that indicates is the instance stored in cache item or not.

        Parameters
        ----------
        inst : str
            Instance name.

        Returns
        -------
        bool
            True if instance is already stored, False otherwise.

        """
        return inst in self.fields_by_inst


@dataclasses.dataclass
class CacheItems:
    """Container for CacheItem instances."""

    _items: List[CacheItem] = dataclasses.field(init=False, default_factory=list)

    def add(self, inst: str, fields: List[Any]):
        """Add item as a key-value pair to CacheItems container.

        Parameters
        ----------
        inst : str
            Instance name.
        fields : List[Any]
            Instance fields.
        """
        item = CacheItem()
        item.add(inst, fields)
        self._items.append(item)

    def get_item_without(self, inst: str):
        """
        Gets cache item without particular instance.

        Parameters
        ----------
        inst : str
            Instance name.

        Returns
        -------
        item : CacheItem
            CacheItem that does not contain particular instance.

        """
        for item in self._items:
            if not item.has(inst):
                return item

        raise ValueError(f"Cannot get item without inst={inst}.")

    def __iter__(self):
        self._n = 0
        return self

    def __next__(self):
        if self._n < len(self._items):
            result = self._items[self._n]
            self._n += 1
            return result
        raise StopIteration


@dataclasses.dataclass
class DateCache:
    """
    Cache for data items that belong to particular date.

    DateCache has the following structure:

    Example
    -------
    DateCache {
        'date_1': CacheItems [
            CacheItem {
                dict {
                    'inst_A': [1, 2, 3],
                    'inst_B': [1, 2, 3]
                }
            },
            CacheItem {
                dict {
                    'inst_A': [1, 2, 3]
                }
            }
        ]
    }
    """

    _cache: Dict[TimestampOrNaT, CacheItems] = dataclasses.field(init=False, default_factory=dict)

    def can_update_fields(self, date: TimestampOrNaT, inst: str) -> bool:
        """
        Boolean that indicates can item fields be updated or not.

        Parameters
        ----------
        date : TimestampOrNaT
            Date string to retrieve a bunch of items that belong to this date.
        inst : str
            Instance name to check if CacheItems has this instance or not.

        Returns
        -------
        bool
            True if fields can be updated, False otherwise
        """
        for item in self._cache.get(date, CacheItems()):
            if not item.has(inst):
                return True

        return False

    def add(self, date: TimestampOrNaT, inst: str, fields: List[Any]):
        """Add items to CacheItems container in data cache during initialization.

        Parameters
        ----------
        date : TimestampOrNaT
            Date string.
        inst : str
            Instance name.
        fields : List[Any]
            Instance fields, filled according template.
        """
        items = self._cache.setdefault(date, CacheItems())
        items.add(inst, fields)

    def update_fields(
        self,
        date: TimestampOrNaT,
        inst: str,
        fields: List[Any],
        num_columns: int,
        unique_insts: List[str],
    ) -> List[Any]:
        """Updates fields in data cache and returns updated ones.

        Parameters
        ----------
        date : TimestampOrNaT
            Date string.
        inst : str
            Instance name.
        fields : List[Any]
            Fields list.
        num_columns : int
            Data columns quantity.
        unique_insts : List[str]
            List of unique instances across dataframe.

        Returns
        -------
        cache_fields : List[Any]
            List of updated fields.
        """
        fields_by_inst = self._cache[date].get_item_without(inst).fields_by_inst
        idx = max(unique_insts.index(inst) for inst in fields_by_inst.keys())
        cache_inst = unique_insts[idx]
        cache_fields = fields_by_inst[cache_inst]
        idx = unique_insts.index(inst)
        cache_idx = unique_insts.index(cache_inst)

        left_idx = cache_idx * num_columns + num_columns
        right_idx = idx * num_columns + num_columns

        for idx in range(left_idx, right_idx):
            cache_fields[idx] = fields[idx]

        fields_by_inst[inst] = cache_fields
        return cache_fields


def partial_process_index(
    num_unique_insts: int,
    num_columns: int,
    date_cache: DateCache,
    index: List[TimestampOrNaT],
    unique_insts: List[str],
    inst: str,
    date: TimestampOrNaT,
    fields: List[Any],
):
    is_add = True

    if num_unique_insts > 1:
        total = num_unique_insts * num_columns
        template = [pd.NA] * total
        idx = unique_insts.index(inst)
        right_idx = idx * num_columns + num_columns
        left_idx = idx * num_columns
        for item, idx in zip(fields, range(left_idx, right_idx)):
            template[idx] = item

        fields = template

        if date_cache.can_update_fields(date, inst):
            is_add = False
            fields = date_cache.update_fields(date, inst, fields, num_columns, unique_insts)

        else:
            date_cache.add(date, inst, fields)
            index.append(date)

    else:
        index.append(date)

    return fields, is_add


@dataclasses.dataclass
class ADCDFBuilder:
    create_headers: Callable[[DFBuildType, dict, HeaderType], Union["HeadersCLIndex", "HeadersCLDateAsIndex"]]

    def build_index(self, raw_data: dict, header_type: "HeaderType" = HeaderType.TITLE, **_) -> pd.DataFrame:
        data = []
        headers = self.create_headers(DFBuildType.INDEX, raw_data, header_type)
        for fields in raw_data.get("data", []):
            fields = list(fields)

            for idx, item in enumerate(fields):
                if item is None:
                    fields[idx] = pd.NA

            for idx in headers.date_idxs:
                fields[idx] = convert_str_to_timestamp(fields[idx])

            data.append(fields)

        df = pd.DataFrame(data=data, columns=headers.names.columns)
        df = convert_dtypes(df)
        return df

    def build_date_as_index(
        self,
        raw_data: dict,
        header_type: "HeaderType" = HeaderType.TITLE,
        use_multiindex: bool = False,
        **_,
    ) -> pd.DataFrame:
        if not raw_data["data"]:
            return pd.DataFrame()

        headers = self.create_headers(DFBuildType.DATE_AS_INDEX, raw_data, header_type)
        data = []
        index = []
        num_headers_names = len(headers.names)
        date_cache = DateCache()
        fields_list = raw_data["data"]
        unique_insts = get_unique_list(fields[headers.inst_idx] for fields in fields_list)
        num_unique_insts = len(unique_insts)
        process_index = partial(
            partial_process_index,
            num_unique_insts,
            num_headers_names,
            date_cache,
            index,
            unique_insts,
        )
        for fields in fields_list:
            fields: List[Union[str, float, int]] = list(fields)
            date_str = fields[headers.date_idx]

            if not date_str:
                continue

            inst = fields[headers.inst_idx]
            fields.pop(headers.date_idx)
            fields.pop(headers.inst_idx)

            fields = [pd.NA if i in {None, object} else i for i in fields]

            for idx in headers.date_idxs:
                fields[idx] = convert_str_to_timestamp(fields[idx])

            fields, is_add = process_index(inst, convert_str_to_timestamp(date_str), fields)

            is_add and data.append(fields)

        if num_headers_names > 1 and num_unique_insts > 1 or use_multiindex:
            columns = pd.MultiIndex.from_tuples(product(unique_insts, headers.names))

        elif num_unique_insts == 1:
            columns = pd.Index(data=headers.names, name=headers.names.get_index_name(unique_insts))

        elif num_headers_names == 1:
            columns = pd.Index(data=unique_insts, name=headers.names.get_index_name())

        else:
            columns = headers.names

        index = pd.Index(data=index, name=headers.date_name)
        df = pd.DataFrame(data=data, columns=columns, index=index)
        df = convert_dtypes(df)
        df.sort_index(ascending=True, inplace=True)
        return df


def build_dates_calendars_df(raw: Any, **_) -> pd.DataFrame:
    raw = deepcopy(raw)
    add_periods_data = []

    clean_request_items = []
    for item in raw:
        if not item.get("error"):
            clean_request_items.append(item)

    for request_item in clean_request_items:
        if request_item.get("date"):
            request_item["date"] = convert_str_to_timestamp(request_item["date"])

        request_item.pop("holidays", None)
        add_periods_data.append(request_item)

    _df = pd.DataFrame(add_periods_data)

    return _df


def build_dates_calendars_holidays_df(raw: Any, **_) -> pd.DataFrame:
    holidays_data = _dates_calendars_prepare_holidays_data(raw)
    holidays_df = pd.DataFrame(holidays_data)
    return holidays_df


def _dates_calendars_prepare_holidays_data(raw):
    raw = deepcopy(raw)
    holidays_data = []

    for request_item_holiday in raw:
        for holiday in request_item_holiday.get("holidays", []):
            if holiday.get("names"):
                for holiday_name in holiday["names"]:
                    holiday_name["tag"] = request_item_holiday.get("tag")
                    holiday_name["date"] = convert_str_to_timestamp(holiday.get("date"))
                    holidays_data.append(holiday_name)
            else:
                holiday["tag"] = request_item_holiday.get("tag")
                holidays_data.append(holiday)
    return holidays_data


def default_build_df(raw: Any, **_) -> pd.DataFrame:
    df = pd.DataFrame(raw)
    df = convert_dtypes(df)
    return df


def build_dates_calendars_date_schedule_df(raw: Any, **_) -> pd.DataFrame:
    raw = deepcopy(raw)

    _dates = []
    for date in raw.get("dates"):
        _dates.append(convert_str_to_timestamp(date))

    raw["dates"] = _dates
    df = pd.DataFrame(raw)
    return df


def build_empty_df(*_, **__) -> pd.DataFrame:
    return pd.DataFrame()


adc_dfbuilder_rdp = ADCDFBuilder(make_create_adc_headers(DataGridType.RDP, LayerType.CONTENT))
adc_dfbuilder_udf = ADCDFBuilder(make_create_adc_headers(DataGridType.UDF, LayerType.CONTENT))
adc_dfbuilder_fundamental_and_reference_rdp = ADCDFBuilder(
    make_create_adc_headers(DataGridType.RDP, LayerType.CONTENT_FUND_AND_REF)
)


def get_adc_dfbuilder(data_grid_type: DataGridType) -> ADCDFBuilder:
    if data_grid_type == DataGridType.RDP:
        return adc_dfbuilder_rdp

    elif data_grid_type == DataGridType.UDF:
        return adc_dfbuilder_udf

    else:
        raise ValueError(f"Unknown data grid type: {data_grid_type}.")
