"""Module to create and use templated search presets for the discovery search

Use templated search from the "Equity" template that was defined in the config:
>>> import lseg.data as ld
>>> ld.discovery.search_templates["Equity"].search()
"""

from lseg.data.discovery._search_templates.manage import SearchTemplates

__all__ = ["templates"]

templates = SearchTemplates()
