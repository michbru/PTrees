"""
VARIABLE REGISTRY - P-Tree Swedish Stock Analysis
==================================================
This file documents ALL variables, characteristics, and their data sources.
It serves as the single source of truth for the data pipeline.

Based on: Cong et al. (2025) JFE paper - 61 characteristics

Data Sources:
  - FINBAS DAILY: Swedish House of Finance daily stock data (1998-2020)
    Fields: ASK, BID, HIGH, LOW, LAST, OAB (turnover SEK), OAT (volume shares),
            Book value, Dividends, Market capitalization
  - SERRANO: Swedish accounting data via ORGNR (1997-2024)
    Files: bokslut (financial statements), nyckeltal (ratios), ftg (company info)
  - FF: Fama-French factors for Sweden/Europe

Coverage: 53/61 characteristics (86.9%) from FINBAS + SERRANO
  - FINBAS Daily: 20 characteristics (price-based, trading, frictions)
  - SERRANO: 28 characteristics (accounting-based)
  - FINBAS + SERRANO: 5 characteristics (valuation ratios)
  - NOT AVAILABLE: 8 characteristics (need IBES or not reported)

Last updated: 2025-11-28
"""

# =============================================================================
# RAW DATA SOURCES
# =============================================================================

RAW_DATA_SOURCES = {
    'finbas_daily': {
        'file': 'data/raw/finbas/raw_finbas_daily.csv',
        'description': 'Swedish House of Finance DAILY stock data',
        'period': '1997-01 to 2020-12',
        'identifier': 'ISIN',
        'frequency': 'daily',
        'columns': {
            'isin': 'ISIN identifier',
            'ticker': 'Stock ticker (e.g., VOLV-A.SE)',
            'name': 'Company name',
            'marketname': 'Exchange (SSE, NGM, etc.)',
            'currency': 'Trading currency (SEK, EUR)',
            'day': 'Date',
            # Price fields (adjusted for corporate actions)
            'LAST': 'Last traded price (adjusted) - for returns, momentum',
            'BID': 'Bid price (adjusted) - for BASPREAD',
            'ASK': 'Ask price (adjusted) - for BASPREAD',
            'HIGH': 'Daily high (adjusted) - for MAXRET, volatility',
            'LOW': 'Daily low (adjusted) - for volatility',
            # Volume/Turnover fields
            'OAB': 'Turnover in SEK - for DOLVOL, ILL',
            'OAT': 'Volume in shares (adjusted) - for TURN, ZEROTRADE',
            # Fundamental fields
            'bookvalue': 'Book value (total equity) - for BM',
            'dividends': 'Dividends per share (unadjusted) - UNRELIABLE/UNUSED',
            'marketcap': 'Market capitalization - for ME, valuation ratios',
        }
    },
    'finbas_monthly': {
        'file': 'data/raw/finbas/raw_finbas_monthly.csv',
        'description': 'Swedish House of Finance monthly stock data (legacy)',
        'period': '1998-01 to 2020-12',
        'identifier': 'ISIN',
        'frequency': 'monthly',
        'status': 'SUPERSEDED by finbas_daily for most calculations',
        'columns': {
            'isin': 'ISIN identifier',
            'ticker': 'Stock ticker (e.g., VOLV-A.SE)',
            'name': 'Company name',
            'marketname': 'Exchange (SSE, NGM, etc.)',
            'currency': 'Trading currency (SEK, EUR)',
            'day': 'Date',
            'lastad': 'Adjusted closing price',
            'bookvalue': 'Book value (total equity)',
            'dividendyeld': 'Dividend yield (%)',
            'dividendevent': 'Dividend event flag',
            'marketvalue': 'Market cap (this share class)',
            'totalmarketvalue': 'Market cap (all share classes)',
        }
    },
    'serrano': {
        'file': 'data/raw/serrano/Stata_2025/',
        'description': 'Swedish accounting data from Serrano database',
        'period': '1997 to 2024',
        'identifier': 'ORGNR (organization number)',
        'frequency': 'annual',
        'files': {
            'bokslut1-10.dta': 'Annual financial statements (126 variables)',
            'nyckeltal1-10.dta': 'Financial ratios and key figures (17 variables)',
            'ftg1-10.dta': 'Company information incl. SNI industry codes',
        },
        'key_variables': {
            # Income Statement
            'NTOMS': 'Net sales/Revenue',
            'RAVAR': 'Raw materials cost (COGS)',
            'HANDVAR': 'Goods for resale cost (COGS)',
            'PERSKOS': 'Personnel costs',
            'AVSKRIV': 'Depreciation',
            'RORRESUL': 'Operating result/EBIT',
            'SKATTER': 'Tax expense',
            'RESAR': 'Net income/Result for year',
            'BRUTORES': 'Gross profit',
            'FORSKO': 'R&D costs (often missing)',
            # Balance Sheet
            'TILLGSU': 'Total assets',
            'ANLTSU': 'Total fixed assets',
            'BYGGMARK': 'Buildings & Land (PPE)',
            'MASK': 'Machinery (PPE)',
            'KABASU': 'Cash & bank',
            'LAGERSU': 'Total inventory',
            'KUNDFORD': 'Accounts receivable',
            'EKSU': 'Total equity',
            'AKTIEKAP': 'Share capital',
            'LSKSU': 'Total long-term debt',
            'KSKSU': 'Total short-term debt',
            # Other
            'ANTANST': 'Number of employees',
        }
    },
    'fama_french': {
        'file': 'data/raw/FamaFrench2020/',
        'description': 'Fama-French factors for beta/idiosyncratic vol calculation',
        'files': {
            'FF4F_monthly.csv': 'Monthly factors (Mkt-RF, SMB, HML, WML)',
            'FF4F_daily.csv': 'Daily factors for daily regressions',
        }
    }
}

# =============================================================================
# INTERMEDIATE DATA
# =============================================================================

INTERMEDIATE_DATA = {
    'finbas_daily_clean': {
        'file': 'data/intermediate/finbas/finbas_daily_clean.csv',
        'source': 'finbas_daily',
        'description': 'Cleaned Finbas daily data - Swedish SEK stocks only',
        'columns': ['isin', 'ticker', 'name', 'exchange', 'date', 'year', 'month',
                    'last', 'bid', 'ask', 'high', 'low', 'oab', 'oat',
                    'book_value', 'market_cap']
    },
    'finbas_clean': {
        'file': 'data/intermediate/finbas/finbas_clean.csv',
        'source': 'finbas_monthly',
        'description': 'Cleaned Finbas monthly data - Swedish SEK stocks only (legacy)',
        'columns': ['isin', 'ticker', 'name', 'exchange', 'date', 'year', 'month',
                    'price', 'book_value', 'market_cap', 'total_market_cap', 'dividend_yield']
    },
    'serrano_accounting': {
        'file': 'data/intermediate/serrano/serrano_accounting.csv',
        'source': 'serrano',
        'description': 'Processed Serrano accounting data (all years merged)',
        'columns': ['orgnr', 'fiscal_year', 'fiscal_year_start', 'fiscal_year_end', 
                    'sales', 'cogs_materials', 'cogs_goods',
                    'personnel_expense', 'depreciation', 'operating_income',
                    'interest_income', 'interest_expense', 'tax_expense', 'net_income',
                    'total_assets', 'fixed_assets', 'intangible_assets', 'tangible_assets',
                    'ppe_buildings', 'ppe_machinery', 'current_assets', 'inventory',
                    'cash', 'receivables', 'book_equity', 'share_capital',
                    'long_term_debt', 'current_liabilities', 'accounts_payable',
                    'num_employees', 'active_status',
                    'roe', 'roa', 'asset_turnover', 'operating_margin',
                    'net_margin', 'sales_growth', 'debt_equity_ratio', 'equity_ratio', 'quick_ratio']
    },
    'isin_orgnr_mapping': {
        'file': 'data/mappings/isin_orgnr_final.csv',
        'source': 'constructed',
        'description': 'Mapping between ISIN and ORGNR for Serrano linkage',
    },
    'stock_with_accounting': {
        'file': 'data/intermediate/stock_with_accounting.csv',
        'source': 'finbas + serrano',
        'description': 'Merged stock and accounting data',
    }
}

# =============================================================================
# PAPER CHARACTERISTICS (61 from Cong et al. 2025)
# =============================================================================

CHARACTERISTICS = {
    # =========================================================================
    # MOMENTUM (9 characteristics)
    # =========================================================================
    'ABR': {
        'name': 'Abnormal Returns',
        'description': 'Abnormal returns around earnings announcements',
        'category': 'momentum',
        'paper_number': 1,
        'source': None,
        'can_calculate': False,
        'reason': 'Requires earnings announcement dates (not available)',
    },
    'CHTX': {
        'name': 'Change in Tax Expense',
        'description': 'Percentage change in tax expense',
        'category': 'momentum',
        'paper_number': 16,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'tax_t / tax_t-1 - 1',
        'lag': '1 year (accounting)',
    },
    'DEPR': {
        'name': 'Depreciation Rate',
        'description': 'Depreciation divided by PP&E',
        'category': 'momentum',
        'paper_number': 18,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'depreciation / ppe',
        'lag': '1 year (accounting)',
    },
    'MOM12M': {
        'name': 'Momentum 12 Month',
        'description': 'Cumulative returns over months t-12 to t-2',
        'category': 'momentum',
        'paper_number': 32,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'price_t-2 / price_t-12 - 1',
        'lag': 'none',
    },
    'MOM1M': {
        'name': 'Short-term Reversal',
        'description': 'Previous month return',
        'category': 'momentum',
        'paper_number': 33,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'price_t / price_t-1 - 1',
        'lag': 'none',
    },
    'MOM36M': {
        'name': 'Momentum 36 Month',
        'description': 'Cumulative returns over months t-36 to t-13',
        'category': 'momentum',
        'paper_number': 34,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'price_t-13 / price_t-36 - 1',
        'lag': 'none',
    },
    'MOM60M': {
        'name': 'Momentum 60 Month',
        'description': 'Cumulative returns over months t-60 to t-13',
        'category': 'momentum',
        'paper_number': 35,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'price_t-13 / price_t-60 - 1',
        'lag': 'none',
    },
    'MOM6M': {
        'name': 'Momentum 6 Month',
        'description': 'Cumulative returns over months t-6 to t-2',
        'category': 'momentum',
        'paper_number': 36,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'price_t-2 / price_t-6 - 1',
        'lag': 'none',
    },
    'NINCR': {
        'name': 'Number of Earnings Increases',
        'description': 'Count of consecutive quarterly earnings increases',
        'category': 'momentum',
        'paper_number': 38,
        'source': None,
        'can_calculate': False,
        'reason': 'Requires quarterly earnings history (not available)',
    },
    'RSUP': {
        'name': 'Revenue Surprise',
        'description': 'Actual revenue minus analyst forecast',
        'category': 'momentum',
        'paper_number': 50,
        'source': None,
        'can_calculate': False,
        'reason': 'Requires analyst revenue forecasts (IBES)',
    },
    'SUE': {
        'name': 'Standardized Unexpected Earnings',
        'description': 'Actual EPS minus analyst forecast, standardized',
        'category': 'momentum',
        'paper_number': 59,
        'source': None,
        'can_calculate': False,
        'reason': 'Requires analyst EPS forecasts (IBES)',
    },
    
    # =========================================================================
    # VALUE-VERSUS-GROWTH (11 characteristics)
    # =========================================================================
    'BM': {
        'name': 'Book-to-Market',
        'description': 'Book equity divided by market equity',
        'category': 'value',
        'paper_number': 9,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'book_value / market_cap',
        'lag': 'none',
    },
    'BM_IA': {
        'name': 'Industry-Adjusted Book-to-Market',
        'description': 'BM minus industry median BM',
        'category': 'value',
        'paper_number': 10,
        'source': 'finbas_daily + serrano',
        'can_calculate': True,
        'formula': 'BM - industry_median(BM)',
        'lag': 'none',
        'note': 'Industry from Serrano SNI codes (ftg files)',
    },
    'CASH': {
        'name': 'Cash Holdings',
        'description': 'Cash and short-term investments to total assets',
        'category': 'value',
        'paper_number': 11,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'cash / total_assets',
        'lag': '1 year (accounting)',
    },
    'CASHDEBT': {
        'name': 'Cash to Debt',
        'description': 'Cash holdings divided by total debt',
        'category': 'value',
        'paper_number': 12,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'cash / total_debt',
        'lag': '1 year (accounting)',
    },
    'CFP': {
        'name': 'Cash Flow to Price',
        'description': 'Operating cash flow divided by market cap',
        'category': 'value',
        'paper_number': 13,
        'source': 'finbas_daily + serrano',
        'can_calculate': True,
        'formula': 'operating_cashflow / market_cap',
        'lag': '1 year (accounting) + 1 month (market)',
    },
    'DY': {
        'name': 'Dividend Yield',
        'description': 'Annual dividend divided by price',
        'category': 'value',
        'paper_number': 20,
        'source': None,
        'can_calculate': False,
        'reason': 'Dividend data in Finbas is event-based and unreliable (35% missing)',
    },
    'EP': {
        'name': 'Earnings to Price',
        'description': 'Net income divided by market cap',
        'category': 'value',
        'paper_number': 21,
        'source': 'finbas_daily + serrano',
        'can_calculate': True,
        'formula': 'net_income / market_cap',
        'lag': '1 year (accounting) + 1 month (market)',
    },
    'LEV': {
        'name': 'Leverage',
        'description': 'Total debt divided by total assets',
        'category': 'value',
        'paper_number': 27,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'total_debt / total_assets',
        'lag': '1 year (accounting)',
    },
    'SGR': {
        'name': 'Sales Growth',
        'description': 'Annual percentage change in sales',
        'category': 'value',
        'paper_number': 55,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'sales_t / sales_t-1 - 1',
        'lag': '1 year (accounting)',
    },
    'SP': {
        'name': 'Sales to Price',
        'description': 'Sales divided by market cap',
        'category': 'value',
        'paper_number': 56,
        'source': 'finbas_daily + serrano',
        'can_calculate': True,
        'formula': 'sales / market_cap',
        'lag': '1 year (accounting) + 1 month (market)',
    },
    
    # =========================================================================
    # INVESTMENT (12 characteristics)
    # =========================================================================
    'ACC': {
        'name': 'Operating Accruals',
        'description': 'Change in working capital minus depreciation, scaled by assets',
        'category': 'investment',
        'paper_number': 2,
        'source': 'serrano',
        'can_calculate': True,
        'formula': '(delta_working_capital - depreciation) / avg_assets',
        'lag': '1 year (accounting)',
    },
    'AGR': {
        'name': 'Asset Growth',
        'description': 'Annual percentage change in total assets',
        'category': 'investment',
        'paper_number': 4,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'total_assets_t / total_assets_t-1 - 1',
        'lag': '1 year (accounting)',
    },
    'CHCSHO': {
        'name': 'Change in Shares Outstanding',
        'description': 'Annual percentage change in shares outstanding',
        'category': 'investment',
        'paper_number': 14,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'shares_t / shares_t-1 - 1',
        'lag': '1 year (accounting)',
    },
    'CINVEST': {
        'name': 'Corporate Investment',
        'description': 'Change in capital expenditure scaled by lagged PPE',
        'category': 'investment',
        'paper_number': 17,
        'source': 'serrano',
        'can_calculate': True,
        'formula': '(capex_t - capex_t-1) / ppe_t-1',
        'lag': '1 year (accounting)',
    },
    'GMA': {
        'name': 'Gross Profitability',
        'description': 'Gross profit divided by total assets',
        'category': 'investment',
        'paper_number': 22,
        'source': 'serrano',
        'can_calculate': True,
        'formula': '(revenue - cogs) / total_assets',
        'lag': '1 year (accounting)',
    },
    'GRLTNOA': {
        'name': 'Growth in Long-term NOA',
        'description': 'Growth in long-term net operating assets',
        'category': 'investment',
        'paper_number': 23,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'Complex - see paper',
        'lag': '1 year (accounting)',
    },
    'LGR': {
        'name': 'Long-term Debt Growth',
        'description': 'Annual percentage change in long-term debt',
        'category': 'investment',
        'paper_number': 28,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'lt_debt_t / lt_debt_t-1 - 1',
        'lag': '1 year (accounting)',
    },
    'NI': {
        'name': 'Net Equity Issuance',
        'description': 'Net equity issuance scaled by lagged market cap',
        'category': 'investment',
        'paper_number': 37,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'log(shares_t / shares_t-1)',
        'lag': '1 year (accounting)',
    },
    'NOA': {
        'name': 'Net Operating Assets',
        'description': 'Operating assets minus operating liabilities, scaled',
        'category': 'investment',
        'paper_number': 39,
        'source': 'serrano',
        'can_calculate': True,
        'formula': '(OA - OL) / lagged_assets',
        'lag': '1 year (accounting)',
    },
    'PCTACC': {
        'name': 'Percent Operating Accruals',
        'description': 'Accruals scaled by absolute value of earnings',
        'category': 'investment',
        'paper_number': 41,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'accruals / abs(net_income)',
        'lag': '1 year (accounting)',
    },
    
    # =========================================================================
    # PROFITABILITY (8 characteristics)
    # =========================================================================
    'ATO': {
        'name': 'Asset Turnover',
        'description': 'Sales divided by average total assets',
        'category': 'profitability',
        'paper_number': 6,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'sales / avg_total_assets',
        'lag': '1 year (accounting)',
    },
    'CHPM': {
        'name': 'Change in Profit Margin',
        'description': 'Change in net income to sales ratio',
        'category': 'profitability',
        'paper_number': 15,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'PM_t - PM_t-1',
        'lag': '1 year (accounting)',
    },
    'OP': {
        'name': 'Operating Profitability',
        'description': 'Operating income minus interest expense, scaled by book equity',
        'category': 'profitability',
        'paper_number': 40,
        'source': 'serrano',
        'can_calculate': True,
        'formula': '(revenue - cogs - sga - interest) / book_equity',
        'lag': '1 year (accounting)',
    },
    'PM': {
        'name': 'Profit Margin',
        'description': 'Net income divided by sales',
        'category': 'profitability',
        'paper_number': 42,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'net_income / sales',
        'lag': '1 year (accounting)',
    },
    'PS': {
        'name': 'Performance Score',
        'description': 'Composite score from multiple performance metrics',
        'category': 'profitability',
        'paper_number': 43,
        'source': None,
        'can_calculate': False,
        'reason': 'Complex composite requiring many inputs',
    },
    'RNA': {
        'name': 'Return on Net Operating Assets',
        'description': 'Operating income divided by net operating assets',
        'category': 'profitability',
        'paper_number': 47,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'operating_income / NOA',
        'lag': '1 year (accounting)',
    },
    'ROA': {
        'name': 'Return on Assets',
        'description': 'Net income divided by total assets',
        'category': 'profitability',
        'paper_number': 48,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'net_income / total_assets',
        'lag': '1 year (accounting)',
    },
    'ROE': {
        'name': 'Return on Equity',
        'description': 'Net income divided by book equity',
        'category': 'profitability',
        'paper_number': 49,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'net_income / book_equity',
        'lag': '1 year (accounting)',
    },
    
    # =========================================================================
    # FRICTIONS (17 characteristics)
    # =========================================================================
    'BASPREAD': {
        'name': 'Bid-Ask Spread',
        'description': 'Average bid-ask spread over past 3 months',
        'category': 'frictions',
        'paper_number': 7,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'mean((ask - bid) / ((ask + bid) / 2)) over 3 months',
        'lag': 'none',
    },
    'BETA': {
        'name': 'Market Beta',
        'description': 'CAPM beta estimated over trailing 36 months',
        'category': 'frictions',
        'paper_number': 8,
        'source': 'finbas_daily + fama_french',
        'can_calculate': True,
        'formula': 'cov(r_i, r_m) / var(r_m) over 36 months of monthly returns',
        'lag': 'none',
        'note': 'Aggregate daily to monthly returns, require min 24 months',
    },
    'DOLVOL': {
        'name': 'Dollar Trading Volume',
        'description': 'Average daily trading volume in SEK',
        'category': 'frictions',
        'paper_number': 19,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'log(mean(OAB)) over 3 months, where OAB = turnover in SEK',
        'lag': 'none',
    },
    'ILL': {
        'name': 'Illiquidity',
        'description': 'Amihud illiquidity ratio (|return| / volume)',
        'category': 'frictions',
        'paper_number': 26,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'mean(|daily_return| / OAB) * 10^6 over 3 months',
        'lag': 'none',
    },
    'MAXRET': {
        'name': 'Maximum Daily Return',
        'description': 'Maximum daily return over past 3 months',
        'category': 'frictions',
        'paper_number': 29,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'max(daily_return) over 3 months',
        'lag': 'none',
    },
    'ME': {
        'name': 'Market Equity',
        'description': 'Market capitalization (price * shares outstanding)',
        'category': 'frictions',
        'paper_number': 30,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'market_cap from Finbas Daily',
        'lag': 'none',
    },
    'ME_IA': {
        'name': 'Industry-Adjusted Size',
        'description': 'Market cap minus industry median market cap',
        'category': 'frictions',
        'paper_number': 31,
        'source': 'finbas_daily + serrano',
        'can_calculate': True,
        'formula': 'ME - industry_median(ME)',
        'lag': 'none',
        'note': 'Industry from Serrano SNI codes (ftg files)',
    },
    'RVAR_CAPM': {
        'name': 'Idiosyncratic Volatility (CAPM)',
        'description': 'Variance of CAPM residuals over 3 months',
        'category': 'frictions',
        'paper_number': 51,
        'source': 'finbas_daily + fama_french',
        'can_calculate': True,
        'formula': 'var(residuals) from r_i = alpha + beta * r_m + epsilon, min 50 days',
        'lag': 'none',
    },
    'RVAR_FF3': {
        'name': 'Idiosyncratic Volatility (FF3)',
        'description': 'Variance of FF3 residuals over 3 months',
        'category': 'frictions',
        'paper_number': 52,
        'source': 'finbas_daily + fama_french',
        'can_calculate': True,
        'formula': 'var(residuals) from FF3 regression, min 50 days',
        'lag': 'none',
    },
    'SVAR': {
        'name': 'Return Variance',
        'description': 'Return variance over past 3 months',
        'category': 'frictions',
        'paper_number': 53,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'var(daily_returns) over 3 months',
        'lag': 'none',
    },
    'SEAS1A': {
        'name': '1-Year Seasonality',
        'description': 'Return in same calendar month last year',
        'category': 'intangibles',
        'paper_number': 54,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'return_t-12 (same calendar month last year)',
        'lag': 'none',
    },
    'STD_DOLVOL': {
        'name': 'Std of Dollar Volume',
        'description': 'Standard deviation of daily SEK volume over 3 months',
        'category': 'frictions',
        'paper_number': 57,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'std(log(OAB)) over 3 months',
        'lag': 'none',
    },
    'STD_TURN': {
        'name': 'Std of Turnover',
        'description': 'Standard deviation of daily turnover over 3 months',
        'category': 'frictions',
        'paper_number': 58,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'std(OAT / shares_outstanding) over 3 months',
        'lag': 'none',
        'note': 'shares_outstanding = market_cap / price',
    },
    'TURN': {
        'name': 'Share Turnover',
        'description': 'Trading volume divided by shares outstanding',
        'category': 'frictions',
        'paper_number': 60,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'mean(OAT / (market_cap / price)) over 3 months',
        'lag': 'none',
    },
    'ZEROTRADE': {
        'name': 'Zero Trading Days',
        'description': 'Number of zero-volume days over past 3 months',
        'category': 'frictions',
        'paper_number': 61,
        'source': 'finbas_daily',
        'can_calculate': True,
        'formula': 'count(OAT == 0) / trading_days over 3 months',
        'lag': 'none',
    },
    
    # =========================================================================
    # INTANGIBLES (8 characteristics)
    # =========================================================================
    'ADM': {
        'name': 'Advertising to Market',
        'description': 'Advertising expense divided by market cap',
        'category': 'intangibles',
        'paper_number': 3,
        'source': None,
        'can_calculate': False,
        'reason': 'Swedish firms do not separately report advertising expense',
    },
    'ALM': {
        'name': 'Asset Liquidity',
        'description': 'Quarterly asset liquidity measure',
        'category': 'intangibles',
        'paper_number': 5,
        'source': None,
        'can_calculate': False,
        'reason': 'Requires quarterly balance sheet data',
    },
    'HERF': {
        'name': 'Industry Concentration',
        'description': 'Herfindahl-Hirschman Index of industry sales',
        'category': 'intangibles',
        'paper_number': 24,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'sum(market_share^2) for industry based on SNI codes',
        'lag': '1 year (accounting)',
        'note': 'Industry from Serrano ftg files (SNI2002, SNI2007, SNI92 codes)',
    },
    'HIRE': {
        'name': 'Employee Growth',
        'description': 'Annual percentage change in number of employees',
        'category': 'intangibles',
        'paper_number': 25,
        'source': 'serrano',
        'can_calculate': True,
        'formula': 'employees_t / employees_t-1 - 1',
        'lag': '1 year (accounting)',
    },
    'RD_SALE': {
        'name': 'R&D to Sales',
        'description': 'R&D expense divided by sales',
        'category': 'intangibles',
        'paper_number': 44,
        'source': None,
        'can_calculate': False,
        'reason': 'Swedish firms often do not separately report R&D',
    },
    'RDM': {
        'name': 'R&D to Market',
        'description': 'R&D expense divided by market cap',
        'category': 'intangibles',
        'paper_number': 45,
        'source': None,
        'can_calculate': False,
        'reason': 'Swedish firms often do not separately report R&D',
    },
    'RE': {
        'name': 'Analyst Earnings Revisions',
        'description': 'Revisions in analyst earnings forecasts',
        'category': 'intangibles',
        'paper_number': 46,
        'source': None,
        'can_calculate': False,
        'reason': 'Requires IBES analyst forecast data',
    },
}

# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

def get_summary():
    """Print summary of characteristic availability."""
    can_calc = [k for k, v in CHARACTERISTICS.items() if v.get('can_calculate', False)]
    cannot_calc = [k for k, v in CHARACTERISTICS.items() if not v.get('can_calculate', False)]
    
    by_category = {}
    for k, v in CHARACTERISTICS.items():
        cat = v['category']
        if cat not in by_category:
            by_category[cat] = {'can': 0, 'cannot': 0}
        if v.get('can_calculate', False):
            by_category[cat]['can'] += 1
        else:
            by_category[cat]['cannot'] += 1
    
    print("=" * 60)
    print("CHARACTERISTIC AVAILABILITY SUMMARY")
    print("=" * 60)
    print(f"\nTotal characteristics in paper: 61")
    print(f"Can calculate: {len(can_calc)} ({len(can_calc)/61*100:.1f}%)")
    print(f"Cannot calculate: {len(cannot_calc)} ({len(cannot_calc)/61*100:.1f}%)")
    print("\nBy category:")
    for cat, counts in sorted(by_category.items()):
        total = counts['can'] + counts['cannot']
        print(f"  {cat:20s}: {counts['can']:2d}/{total:2d} ({counts['can']/total*100:.0f}%)")
    
    print("\n" + "=" * 60)
    print("CHARACTERISTICS WE CAN CALCULATE")
    print("=" * 60)
    for char in sorted(can_calc):
        info = CHARACTERISTICS[char]
        print(f"  {char:10s} | {info['source']:20s} | {info['name']}")
    
    print("\n" + "=" * 60)
    print("CHARACTERISTICS WE CANNOT CALCULATE")
    print("=" * 60)
    for char in sorted(cannot_calc):
        info = CHARACTERISTICS[char]
        reason = info.get('reason', 'Unknown')
        print(f"  {char:10s} | {reason}")
    
    return can_calc, cannot_calc

def get_characteristics_by_source(source):
    """Get all characteristics that use a specific source."""
    return [k for k, v in CHARACTERISTICS.items() 
            if v.get('source') and source in str(v.get('source', ''))]

def get_finbas_characteristics():
    """Get characteristics calculable from Finbas alone."""
    return get_characteristics_by_source('finbas')

def get_serrano_characteristics():
    """Get characteristics requiring Serrano data."""
    return get_characteristics_by_source('serrano')


if __name__ == '__main__':
    get_summary()
