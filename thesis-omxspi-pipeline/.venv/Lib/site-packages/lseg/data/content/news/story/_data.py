import warnings
from dataclasses import dataclass
from typing import List, Optional, Union

import pandas as pd
from pandas.core.tools.datetimes import DatetimeScalar

from .. import Urgency
from .._tools import _get_headline_from_story
from ...._tools import get_from_path, cached_property, get_list_from_path
from ....delivery._data._endpoint_data import EndpointData


class NewsStoryContent:
    def __init__(self, html: str, text: str, web_url: str):
        self.html = html
        self.text = text
        self.web_url = web_url

    def __eq__(self, other):
        return self.html == other.html and self.text == other.text and self.web_url == other.web_url


@dataclass
class Story:
    def __init__(self, raw_story: dict):
        self._raw_story = raw_story

    @cached_property
    def version(self) -> str:
        return get_from_path(self._raw_story, "newsItem._version")

    @cached_property
    def audience(self) -> List[str]:
        return get_list_from_path(self._raw_story, "newsItem.contentMeta.audience", "_qcode")

    @cached_property
    def creator(self) -> str:
        return get_from_path(self._raw_story, "newsItem.contentMeta.creator.0._qcode")

    @cached_property
    def source(self) -> List[dict]:
        warnings.warn(
            "This property has been deprecated and will be removed in future v2.2.0 version. Use info_source instead.",
            category=FutureWarning,
        )
        return get_from_path(self._raw_story, "newsItem.contentMeta.infoSource")

    @cached_property
    def info_source(self) -> List[dict]:
        return get_from_path(self._raw_story, "newsItem.contentMeta.infoSource")

    @cached_property
    def language(self) -> List[str]:
        return get_list_from_path(self._raw_story, "newsItem.contentMeta.language", "_tag")

    @cached_property
    def item_codes(self) -> List[str]:
        warnings.warn(
            "This property has been deprecated and will be removed in future v2.2.0 version. Use subject_codes instead.",
            category=FutureWarning,
        )
        return get_list_from_path(self._raw_story, "newsItem.contentMeta.subject", "_qcode")

    @cached_property
    def subject_codes(self) -> List[str]:
        return get_list_from_path(self._raw_story, "newsItem.contentMeta.subject", "_qcode")

    @cached_property
    def urgency(self) -> int:
        urgency = get_from_path(self._raw_story, "newsItem.contentMeta.urgency.$")
        return Urgency(urgency) if urgency else Urgency.Unknown

    @cached_property
    def creation_date(self) -> "DatetimeScalar":
        warnings.warn(
            message="This property has been deprecated and will be removed in future v2.2.0 version."
            + " Use first_created instead.",
            category=FutureWarning,
        )
        return pd.to_datetime(get_from_path(self._raw_story, "newsItem.itemMeta.firstCreated.$"))

    @cached_property
    def first_created(self) -> "DatetimeScalar":
        return pd.to_datetime(get_from_path(self._raw_story, "newsItem.itemMeta.firstCreated.$"))

    @cached_property
    def update_date(self) -> "DatetimeScalar":
        warnings.warn(
            message="This property has been deprecated and will be removed in future v2.2.0 version."
            + "Use version_created instead.",
            category=FutureWarning,
        )
        return pd.to_datetime(get_from_path(self._raw_story, "newsItem.itemMeta.versionCreated.$"))

    @cached_property
    def version_created(self) -> "DatetimeScalar":
        return pd.to_datetime(get_from_path(self._raw_story, "newsItem.itemMeta.versionCreated.$"))

    @cached_property
    def title(self) -> str:
        return get_from_path(self._raw_story, "newsItem.itemMeta.title.0.$")

    @cached_property
    def assert_codes(self) -> List[str]:
        return get_list_from_path(self._raw_story, "newsItem.contentMeta.assert", "_qcode")

    @cached_property
    def content(self) -> NewsStoryContent:
        inline_xml = get_from_path(self._raw_story, "newsItem.contentSet.inlineXML")
        html = get_from_path(inline_xml, get_item_path(inline_xml))
        inline_data = get_from_path(self._raw_story, "newsItem.contentSet.inlineData")
        text = get_from_path(inline_data, get_item_path(inline_data))
        web_url = get_from_path(self._raw_story, "webURL")
        return NewsStoryContent(html, text, web_url)

    @cached_property
    def topnews_metadata(self) -> List[str]:
        return get_from_path(self._raw_story, "topNewsMetadata")

    @cached_property
    def notifications(self) -> List[str]:
        return get_from_path(self._raw_story, "notifications")

    @cached_property
    def headline(self) -> str:
        return _get_headline_from_story(self._raw_story)


def get_item_path(items: Union[dict, list]) -> str:
    return "0.$" if isinstance(items, list) else "$"


def story_from_dict(raw_story: dict) -> Story:
    return Story(raw_story)


@dataclass
class NewsStoryData(EndpointData):
    _story: Optional[Story] = None

    @staticmethod
    def _build_story(raw: dict) -> Story:
        return story_from_dict(raw)

    @property
    def story(self) -> Story:
        if self._story is None:
            self._story = self._build_story(self.raw)
        return self._story
