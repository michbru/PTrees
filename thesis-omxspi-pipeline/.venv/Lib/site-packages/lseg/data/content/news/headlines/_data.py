import warnings
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
from pandas.core.tools.datetimes import DatetimeScalar

from .. import Urgency
from .._tools import get_headlines
from ..._content_data import Data
from ...._tools import get_from_path, cached_property, get_list_from_path
from ...._types import OptInt


class Headline:
    def __init__(self, raw_headline: dict):
        self._raw_headline = raw_headline

    @cached_property
    def story_id(self) -> str:
        return get_from_path(self._raw_headline, "storyId") if self._raw_headline else None

    @cached_property
    def version(self) -> str:
        return get_from_path(self._raw_headline, "newsItem.version") if self._raw_headline else None

    @cached_property
    def first_created(self) -> "DatetimeScalar":
        return (
            pd.to_datetime(get_from_path(self._raw_headline, "newsItem.itemMeta.firstCreated.$"))
            if self._raw_headline
            else None
        )

    @cached_property
    def version_created(self) -> "DatetimeScalar":
        return pd.to_datetime(get_from_path(self._raw_headline, "newsItem.itemMeta.versionCreated.$"))

    @cached_property
    def title(self) -> str:
        return get_from_path(self._raw_headline, "newsItem.itemMeta.title.0.$")

    @cached_property
    def audience(self) -> str:
        return self._raw_headline.get("storyId", None)

    @cached_property
    def creator(self) -> str:
        return get_from_path(self._raw_headline, "newsItem.contentMeta.creator.0._qcode")

    @cached_property
    def source(self) -> List[dict]:
        warnings.warn(
            "This property has been deprecated and will be removed in future v2.2.0 version. Use info_source instead.",
            category=FutureWarning,
        )
        return get_from_path(self._raw_headline, "newsItem.contentMeta.infoSource")

    @cached_property
    def info_source(self) -> List[dict]:
        return get_from_path(self._raw_headline, "newsItem.contentMeta.infoSource")

    @cached_property
    def language(self) -> List[dict]:
        return get_from_path(self._raw_headline, "newsItem.contentMeta.language")

    @cached_property
    def item_codes(self) -> List[str]:
        warnings.warn(
            "This property has been deprecated and will be removed in future v2.2.0 version. Use subject_codes instead.",
            category=FutureWarning,
        )
        return get_list_from_path(self._raw_story, "newsItem.contentMeta.subject")

    @cached_property
    def subject_codes(self) -> List[str]:
        return get_list_from_path(self._raw_story, "newsItem.contentMeta.subject", "_qcode")

    @cached_property
    def urgency(self) -> Urgency:
        return Urgency(get_from_path(self._raw_headline, "newsItem.contentMeta.urgency.$"))

    @cached_property
    def assert_codes(self) -> List[str]:
        return get_list_from_path(self._raw_story, "newsItem.assert", "_qcode")


@dataclass
class NewsHeadlinesData(Data):
    _headlines: Optional[List["Headline"]] = None
    _limit: "OptInt" = None

    @staticmethod
    def headline_from_dict(headline: dict) -> Headline:
        return Headline(headline)

    @staticmethod
    def _build_headlines(raw: dict, limit: int) -> List["Headline"]:
        return get_headlines(raw, NewsHeadlinesData.headline_from_dict, limit)

    @property
    def headlines(self) -> List["Headline"]:
        if self._headlines is None:
            self._headlines = self._build_headlines(self.raw, self._limit)

        return self._headlines
