import itertools
from typing import List, Union

import pandas as pd

from lseg.data.errors import LDError
from ..._core import session
from ...content import search, fundamental_and_reference


class FutureSuffixGenerator:
    month_codes = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]

    def __init__(self, start_date: pd.Timestamp, end_date: pd.Timestamp, current_date: pd.Timestamp):
        # first day of the month
        expired_end_date = min(end_date, current_date)
        expired_end_date = pd.Timestamp(year=expired_end_date.year, month=expired_end_date.month, day=1)
        future_start_date = max(current_date, start_date)
        future_start_date = pd.Timestamp(year=future_start_date.year, month=future_start_date.month, day=1)

        # split range in expired and non-expired to add the correct suffix
        self.date_range_expired = pd.date_range(start=start_date, end=expired_end_date, freq="MS")
        self.date_range_future = pd.date_range(start=future_start_date, end=end_date, freq="MS")

    def __iter__(self):
        # up to current date
        for date in self.date_range_expired:
            month_code = self.month_codes[date.month - 1]
            year = str(date.year)

            yield month_code + year[-1] + "^" + year[-2]
            yield month_code + year[-2:] + "^" + year[-2]

        # after current date
        for date in self.date_range_future:
            month_code = self.month_codes[date.month - 1]
            year = str(date.year)

            yield month_code + year[-1]
            yield month_code + year[-2:]


def generate_future_ric_queries(ric_roots, start_date, end_date, current_date, count=5000):
    suffix_generator = FutureSuffixGenerator(start_date, end_date, current_date)  # only suffixes
    g1 = itertools.product(ric_roots, suffix_generator)  # ric_roots x suffixes - cartesian product
    g2 = map(lambda x: f"'{''.join(x)}'", g1)  # join the ric root string with the suffix string and add ''

    while chunk := tuple(itertools.islice(g2, count)):
        yield " ".join(chunk)


class RicRootFetcher:
    @staticmethod
    def is_org_perm_id(underlying: str):
        return underlying.isdigit()

    @staticmethod
    def is_ric_root(underlying: str):
        return "." not in underlying and not RicRootFetcher.is_org_perm_id(underlying)

    @staticmethod
    def is_index_ric(underlying):
        return underlying.startswith(".")

    @staticmethod
    def get_ric_root(underlying):
        logger = session.get_default().logger()
        if RicRootFetcher.is_ric_root(underlying):
            return [], [underlying]

        # Construct the query based on the underlying
        query_instr = f"UnderlyingQuoteRIC eq '{underlying}'"
        if not RicRootFetcher.is_index_ric(underlying):
            try:
                # Fetch the org ID for the underlying
                response = fundamental_and_reference.Definition(
                    universe=[underlying], fields=["TR.OrgidCode", "TR.RIC"]
                ).get_data()
                org_id = response.data.df["ORG ID"][0]
                query_instr = f"UnderlyingIssuerOrgid eq '{org_id}'"
            except LDError:
                logger.error(f"Org ID not found for {underlying}, requesting with UnderlyingQuoteRIC")

        current_date = pd.Timestamp.today()
        # Fetch the relevant data from the search API
        response = search.Definition(
            view=search.Views.EQUITY_QUOTES,
            select="ExpiryDate, ShortName, ExchangeName, ExchangeCode, RicRoot, RIC, UnderlyingQuoteRIC, "
            "RCSAssetCategoryLeaf",
            filter=f"{query_instr} and IsChain eq false and AssetState eq 'AC' and RCSAssetClass eq 'FUT' and "
            f"ExpiryDate ge {current_date.strftime('%Y-%m-%d')}",
            top=1000,
        ).get_data()

        # Extract the unique RIC roots and RICs from the response
        ric_roots = []
        rics = []
        if response.data and not response.data.df.empty:
            response_df = response.data.df
            ric_roots = response_df["RicRoot"].unique().tolist()
            rics = response_df[response_df["RIC"] == response_df["RicRoot"]]["RicRoot"].tolist()
        return rics, ric_roots


class Futures:
    def __init__(self, universe: Union[str, List[str]], start: str, end: str):
        """
        Initialize the Futures object with a universe, start date, and end date.

        Parameters
        ----------
        universe : str | list[str]
            A single instrument (RIC, Org PermId or RICRoot) as a string or a list containing one instrument.
        start : str
            The start date for the futures data. String format is: '%Y-%m-%d'.
        end : str
            The end date for the futures data. String format is: '%Y-%m-%d'.

        Returns
        -------
        pd.DataFrame

        Examples
        --------
        >>> from lseg.data.discovery import Futures
        >>> futures = Futures(universe="ES", start="2020-01-01", end="2025-12-31")
        >>> data = futures.get_data()
        >>> print(data)
        """
        self.universe = universe if isinstance(universe, str) else universe[0]
        self.start = pd.to_datetime(start)
        self.end = pd.to_datetime(end)

    def get_data(self):
        return self._get_futures(underlying=self.universe, expiry_start=self.start, expiry_end=self.end)

    @staticmethod
    def _get_futures(underlying, expiry_start, expiry_end):
        logger = session.get_default().logger()

        rics, ric_roots = RicRootFetcher.get_ric_root(underlying)

        if not ric_roots and not rics:
            logger.debug(f"No futures contract found for {underlying} expiring between {expiry_start} and {expiry_end}")
            return pd.DataFrame()

        root_ric_query_strs = generate_future_ric_queries(ric_roots, expiry_start, expiry_end, pd.Timestamp.today())
        ric_query_str = " ".join([f"'{ric}'" for ric in rics])

        responses = []
        for ric_query_str in itertools.chain(root_ric_query_strs, ric_query_str):
            response = (
                search.Definition(
                    view=search.Views.DERIVATIVE_QUOTES,
                    select="DocumentTitle, RIC, RicRoot, ExchangeCode, ExpiryDate, "
                    + "UnderlyingQuoteRIC, RCSAssetCategoryLeaf, RetireDate, ContractMonthYear, ContractType, "
                    + "Periodicity, RCSAssetClass",
                    filter="RCSAssetCategoryLeaf eq '*Future*' and RCSAssetClass eq '*FUT*'"
                    + f" and RIC in ({ric_query_str})",
                    top=10000,
                )
                .get_data()
                .data.df
            )
            if not response.empty:
                responses.append(response)

        if responses:
            combined_response = pd.concat(responses)
            filtered_response = combined_response[
                (combined_response["ExpiryDate"] >= expiry_start) & (combined_response["ExpiryDate"] <= expiry_end)
            ]
            return filtered_response.sort_values("ExpiryDate").reset_index(drop=True)

        logger.debug(f"No futures contract found for {underlying} expiring between {expiry_start} and {expiry_end}")
        return pd.DataFrame()
