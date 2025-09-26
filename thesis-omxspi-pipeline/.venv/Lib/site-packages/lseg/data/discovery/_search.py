from typing import TYPE_CHECKING, Union

from .. import content
from .._types import OptStr
from ..content.search import Views

if TYPE_CHECKING:
    import pandas as pd
    from .._types import ExtendedParams


def search(
    query: OptStr = None,
    view: Union[Views, str] = Views.SEARCH_ALL,
    filter: OptStr = None,
    order_by: OptStr = None,
    boost: OptStr = None,
    select: OptStr = None,
    top: int = 10,
    skip: int = 0,
    group_by: OptStr = None,
    group_count: int = 3,
    features: OptStr = None,
    scope: OptStr = None,
    terms: OptStr = None,
    navigators: OptStr = None,
    extended_params: "ExtendedParams" = None,
) -> "pd.DataFrame":  # NOSONAR
    """
    The search service identifies a matching set of documents which satisfy the caller's criteria, sorts it,
    and selects a subset of the matches to return as the result set. Each step can be controlled via parameters.

    Parameters
    ----------
    query: str, optional
        Keyword argument for view

    view: Views or str, optional
        The view for searching see at Views enum.
        Default: Views.SEARCH_ALL

    filter: str, optional
        Where query is for unstructured end-user-oriented restriction, filter is for
        structured programmatic restriction.

    order_by: str, optional
        Defines the order in which matching documents should be returned.

    boost: str, optional
        This argument supports exactly the same predicate expression syntax as filter,
        but where filter restricts which documents are matched at all,
        boost just applies a large scoring boost to documents it matches,
        which will almost always guarantee that they appear at the top of the results.

    select: str, optional
        A comma-separated list of the properties of a document to be returned in the response.

    top: int, optional
        the maximum number of documents to retrieve. Must be non-negative.
        default: 10

    skip: int, optional
        The number of documents to skip in the sorted result set before returning the
        next top.

    group_by: str, optional
        If specified, this must name a single Groupable property.
        returned documents are grouped into buckets based on their value for this
        property.

    group_count: str, optional
        When supplied in combination with group_by, sets the maximum number of documents
        to be returned per bucket.
        default: 3

    navigators: str, optional
        This can name one or more properties, separated by commas, each of which must
        be Navigable.
        Example: "HullType"

    features: str, optional
        Comma-separated list of flags, typically niche or experimental things which most callers won't want

    scope: str, optional
        Name of a `Symbol` property against which `Terms` will be matched
        Example: "RIC"

    terms: str, optional
        Comma-separated list of up to 5000 symbols to be matched against the `Scope` property
        Example": "A,B,C,D"

    extended_params : dict, optional
        Other parameters can be provided if necessary

    Examples
    --------
    >>> import lseg.data as ld
    >>> df1 = ld.discovery.search(query="cfo", view=ld.discovery.Views.PEOPLE)
    >>> # What's the general distribution of earnings per share in the 0-20 range using fixed-value-width bucket ranges?
    >>> df2 = ld.discovery.search(
    ...     view=ld.discovery.Views.EQUITY_QUOTES,
    ...     top=0,
    ...     filter="Eps gt 0 and Eps lt 20",
    ...     navigators="Eps(type:histogram,buckets:4)"
    ... )
    >>> # Top ten currencies for govcorp bonds, ranked by total outstanding value, along with the maximum coupon of each.
    >>> df3 = ld.discovery.search(
    ...     view=ld.discovery.Views.GOV_CORP_INSTRUMENTS,
    ...     top=0,
    ...     navigators="Currency(buckets:10,desc:sum_FaceOutstandingUSD,calc:max_CouponRate)"
    ... )
    """
    return (
        content.search.Definition(
            query=query,
            view=view,
            filter=filter,
            order_by=order_by,
            boost=boost,
            select=select,
            top=top,
            skip=skip,
            group_by=group_by,
            group_count=group_count,
            navigators=navigators,
            features=features,
            scope=scope,
            terms=terms,
            extended_params=extended_params,
        )
        .get_data()
        .data.df
    )
