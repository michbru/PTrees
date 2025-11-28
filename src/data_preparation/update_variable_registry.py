"""
Script to update VARIABLE_REGISTRY.py with actual implementation details and coverage.
"""

# Coverage data from final run
COVERAGE = {
    'ACC': 35.87,
    'AGR': 79.44,
    'ATO': 79.34,
    'BASPREAD': 98.71,
    'BETA': 0.00,  # Needs FF factors
    'BM': 98.22,
    'CASH': 89.34,
    'CASHDEBT': 88.34,
    'CFP': 41.16,
    'CHCSHO': 88.00,
    'CHPM': 68.49,
    'CHTX': 62.83,
    'CINVEST': 23.79,
    'DEPR': 28.43,
    'DOLVOL': 96.00,
    'EP': 89.23,
    'GMA': 89.36,
    'GRLTNOA': 70.55,
    'HIRE': 73.39,
    'ILL': 94.16,
    'LEV': 89.30,
    'LGR': 57.85,
    'MAXRET': 95.21,
    'ME': 99.79,
    'MOM12M': 88.25,
    'MOM1M': 98.86,
    'MOM36M': 69.52,
    'MOM60M': 55.10,
    'MOM6M': 93.83,
    'NI': 88.00,
    'NOA': 79.13,
    'OP': 89.07,
    'PCTACC': 35.27,
    'PM': 88.18,
    'RNA': 88.96,
    'ROA': 89.22,
    'ROE': 89.02,
    'RVAR_CAPM': 0.00,  # Needs FF factors
    'RVAR_FF3': 0.00,  # Needs FF factors
    'SEAS1A': 88.52,
    'SGR': 66.15,
    'SP': 89.35,
    'STD_DOLVOL': 96.00,
    'STD_TURN': 96.87,
    'SVAR': 95.21,
    'TURN': 96.86,
    'ZEROTRADE': 0.00,  # All zero (no zero-volume days in Swedish market)
}

# Implementation details for each characteristic
IMPLEMENTATIONS = {
    # Momentum
    'CHTX': {
        'formula_actual': 'pct_change(tax_expense_lag12, periods=12)',
        'code': 'df.groupby("isin")["tax_expense_lag12"].pct_change(12)',
        'lag_actual': '12 months (accounting)',
    },
    'DEPR': {
        'formula_actual': 'depreciation_lag12 / (ppe_buildings_lag12 + ppe_machinery_lag12)',
        'code': 'df["depreciation_lag12"] / df["ppe_lag12"]',
        'lag_actual': '12 months (accounting)',
    },
    'MOM1M': {
        'formula_actual': 'shift(ret_monthly, 1)',
        'code': 'df.groupby("isin")["ret_monthly"].shift(1)',
        'lag_actual': 'none',
    },
    'MOM6M': {
        'formula_actual': '(close_lag2 / close_lag6) - 1',
        'code': '(df["close_lag2"] / df["close_lag6"]) - 1',
        'lag_actual': 'none',
    },
    'MOM12M': {
        'formula_actual': '(close_lag2 / close_lag12) - 1',
        'code': '(df["close_lag2"] / df["close_lag12"]) - 1',
        'lag_actual': 'none',
    },
    'MOM36M': {
        'formula_actual': '(close_lag13 / close_lag36) - 1',
        'code': '(df["close_lag13"] / df["close_lag36"]) - 1',
        'lag_actual': 'none',
    },
    'MOM60M': {
        'formula_actual': '(close_lag13 / close_lag60) - 1',
        'code': '(df["close_lag13"] / df["close_lag60"]) - 1',
        'lag_actual': 'none',
    },
    'SEAS1A': {
        'formula_actual': 'shift(ret_monthly, 12)',
        'code': 'df.groupby("isin")["ret_monthly"].shift(12)',
        'lag_actual': 'none',
    },

    # Value
    'BM': {
        'formula_actual': 'book_value / market_cap',
        'code': 'df["book_value"] / df["market_cap"]',
        'lag_actual': 'none (book_value from Finbas is already reported)',
    },
    'CASH': {
        'formula_actual': 'cash_lag12 / total_assets_lag12',
        'code': 'df["cash_lag12"] / df["total_assets_lag12"]',
        'lag_actual': '12 months (accounting)',
    },
    'CASHDEBT': {
        'formula_actual': 'cash_lag12 / (long_term_debt_lag12 + current_liabilities_lag12)',
        'code': 'df["cash_lag12"] / df["total_debt_lag12"]',
        'lag_actual': '12 months (accounting)',
    },
    'CFP': {
        'formula_actual': '(net_income_lag12 + depreciation_lag12) / market_cap_lag1',
        'code': 'df["operating_cashflow"] / df["market_cap_lag1"]',
        'lag_actual': '12 months (accounting) + 1 month (market cap)',
    },
    'EP': {
        'formula_actual': 'net_income_lag12 / market_cap_lag1',
        'code': 'df["net_income_lag12"] / df["market_cap_lag1"]',
        'lag_actual': '12 months (accounting) + 1 month (market cap)',
    },
    'LEV': {
        'formula_actual': '(long_term_debt_lag12 + current_liabilities_lag12) / total_assets_lag12',
        'code': 'df["total_debt_lag12"] / df["total_assets_lag12"]',
        'lag_actual': '12 months (accounting)',
    },
    'SGR': {
        'formula_actual': 'pct_change(sales_lag12, periods=12)',
        'code': 'df.groupby("isin")["sales_lag12"].pct_change(12)',
        'lag_actual': '12 months (accounting)',
    },
    'SP': {
        'formula_actual': 'sales_lag12 / market_cap_lag1',
        'code': 'df["sales_lag12"] / df["market_cap_lag1"]',
        'lag_actual': '12 months (accounting) + 1 month (market cap)',
    },

    # Frictions (Daily-based)
    'BASPREAD': {
        'formula_actual': 'rolling_mean((ask - bid) / ((ask + bid) / 2), window=63)',
        'code': 'df.groupby("isin")["spread"].transform(lambda x: x.rolling(63, min_periods=20).mean())',
        'lag_actual': 'none',
        'note': 'Calculated on daily data, then aggregated to month-end',
    },
    'DOLVOL': {
        'formula_actual': 'log(rolling_mean(turnover_sek, window=63) + 1)',
        'code': 'df.groupby("isin")["turnover_sek"].transform(lambda x: np.log(x.rolling(63, min_periods=20).mean() + 1))',
        'lag_actual': 'none',
        'note': 'Calculated on daily data, then aggregated to month-end',
    },
    'ILL': {
        'formula_actual': 'rolling_mean(abs(ret) / (turnover_sek + 1) * 1e6, window=63)',
        'code': 'df.groupby("isin")["illiq_daily"].transform(lambda x: x.rolling(63, min_periods=20).mean())',
        'lag_actual': 'none',
        'note': 'Amihud illiquidity, calculated on daily data',
    },
    'MAXRET': {
        'formula_actual': 'rolling_max(daily_return, window=63)',
        'code': 'df.groupby("isin")["ret"].transform(lambda x: x.rolling(63, min_periods=20).max())',
        'lag_actual': 'none',
    },
    'ME': {
        'formula_actual': 'log(market_cap)',
        'code': 'np.log(df["market_cap"])',
        'lag_actual': 'none',
    },
    'SVAR': {
        'formula_actual': 'rolling_var(daily_return, window=63)',
        'code': 'df.groupby("isin")["ret"].transform(lambda x: x.rolling(63, min_periods=20).var())',
        'lag_actual': 'none',
    },
    'STD_DOLVOL': {
        'formula_actual': 'rolling_std(log(turnover_sek + 1), window=63)',
        'code': 'df.groupby("isin")["log_dolvol"].transform(lambda x: x.rolling(63, min_periods=20).std())',
        'lag_actual': 'none',
    },
    'STD_TURN': {
        'formula_actual': 'rolling_std(volume / shares_out, window=63)',
        'code': 'df.groupby("isin")["daily_turn"].transform(lambda x: x.rolling(63, min_periods=20).std())',
        'lag_actual': 'none',
        'note': 'Uses market_cap_filled for better coverage',
    },
    'TURN': {
        'formula_actual': 'rolling_mean(volume / shares_out, window=63)',
        'code': 'df.groupby("isin")["daily_turn"].transform(lambda x: x.rolling(63, min_periods=20).mean())',
        'lag_actual': 'none',
        'note': 'Uses market_cap_filled for better coverage',
    },
    'ZEROTRADE': {
        'formula_actual': 'rolling_mean((volume == 0).astype(int), window=63)',
        'code': 'df.groupby("isin")["zero_volume"].transform(lambda x: x.rolling(63, min_periods=20).mean())',
        'lag_actual': 'none',
        'note': 'All values are 0 - Swedish market has NO zero-volume days',
    },
}

print("Coverage and implementation details prepared.")
print(f"Characteristics with coverage data: {len(COVERAGE)}")
print(f"Characteristics with implementation details: {len(IMPLEMENTATIONS)}")
print("\nNOTE: To update VARIABLE_REGISTRY.py, manually add 'coverage' and 'implementation' fields")
print("      to each characteristic using this data.")
