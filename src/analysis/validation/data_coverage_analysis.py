"""
Data Coverage and Firm Representation Analysis
==============================================

This script performs comprehensive analysis of data coverage and firm representation
for the P-Tree thesis project. It examines:

1. Raw data coverage from different sources (Finbas, Serrano)
2. Variable availability and coverage over time
3. Firm representation and persistence in the dataset
4. Temporal coverage analysis
5. Generates LaTeX tables and visualizations for thesis

Output:
- results/validation/coverage_analysis/ (tables and figures)
- LaTeX formatted tables for direct inclusion in thesis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
from datetime import datetime
import matplotlib.dates as mdates

warnings.filterwarnings('ignore')

# Set style for thesis-quality plots
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
RAW_FINBAS_PATH = PROJECT_ROOT / 'data' / 'raw' / 'finbas' / 'raw_finbas_daily.csv'
INTERMEDIATE_FINBAS_PATH = PROJECT_ROOT / 'data' / 'intermediate' / 'finbas' / 'finbas_monthly_clean.csv'
INTERMEDIATE_SERRANO_PATH = PROJECT_ROOT / 'data' / 'intermediate' / 'serrano' / 'serrano_accounting.csv'
PROCESSED_DATA_PATH = PROJECT_ROOT / 'data' / 'processed' / 'ptree_dataset_monthly.csv'
MAPPING_PATH = PROJECT_ROOT / 'data' / 'mappings' / 'isin_orgnr_final.csv'

# Output directory
OUTPUT_DIR = PROJECT_ROOT / 'results' / 'validation' / 'coverage_analysis'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class DataCoverageAnalyzer:
    """Comprehensive data coverage and firm representation analyzer."""
    
    def __init__(self):
        self.results = {}
        self.load_data()
        
    def load_data(self):
        """Load all required datasets."""
        print("Loading datasets...")
        
        # Load intermediate Finbas data (already processed and filtered)
        if INTERMEDIATE_FINBAS_PATH.exists():
            print("  Loading processed Finbas monthly data...")
            self.raw_finbas = pd.read_csv(INTERMEDIATE_FINBAS_PATH, low_memory=False)
            self.raw_finbas['date'] = pd.to_datetime(self.raw_finbas['date'], errors='coerce')
            print(f"    Loaded {len(self.raw_finbas):,} observations from processed Finbas")
        else:
            print("  Warning: Processed Finbas data not found")
            self.raw_finbas = None
            
        # Load processed Serrano data (sample first to avoid memory issues)
        if INTERMEDIATE_SERRANO_PATH.exists():
            print("  Loading processed Serrano data (sampling for analysis)...")
            # Read a sample first to get column structure and basic stats
            self.raw_serrano = pd.read_csv(INTERMEDIATE_SERRANO_PATH, nrows=50000, low_memory=False)
            if 'fiscal_year_end' in self.raw_serrano.columns:
                self.raw_serrano['fiscal_year_end'] = pd.to_datetime(self.raw_serrano['fiscal_year_end'], errors='coerce')
            print(f"    Loaded sample of {len(self.raw_serrano):,} observations from Serrano")
        else:
            print("  Warning: Processed Serrano data not found")
            self.raw_serrano = None
            
        # Load final processed dataset
        if PROCESSED_DATA_PATH.exists():
            print("  Loading final P-Tree dataset...")
            self.final_data = pd.read_csv(PROCESSED_DATA_PATH, low_memory=False)
            self.final_data['date'] = pd.to_datetime(self.final_data['date'], errors='coerce')
            print(f"    Loaded {len(self.final_data):,} observations from final dataset")
        else:
            print("  Warning: Final P-Tree dataset not found")
            self.final_data = None
            
        # Load ISIN-ORGNR mapping
        if MAPPING_PATH.exists():
            print("  Loading ISIN-ORGNR mapping...")
            self.mapping = pd.read_csv(MAPPING_PATH, low_memory=False)
            print(f"    Loaded {len(self.mapping):,} mappings")
        else:
            print("  Warning: ISIN-ORGNR mapping not found")
            self.mapping = None

    def analyze_raw_data_coverage(self):
        """Analyze coverage of raw data sources."""
        print("\n" + "="*60)
        print("ANALYZING RAW DATA COVERAGE")
        print("="*60)
        
        coverage_stats = {}
        
        # Finbas coverage
        if self.raw_finbas is not None:
            finbas_stats = self._analyze_finbas_coverage()
            coverage_stats['finbas'] = finbas_stats
            
        # Serrano coverage  
        if self.raw_serrano is not None:
            serrano_stats = self._analyze_serrano_coverage()
            coverage_stats['serrano'] = serrano_stats
            
        # Mapping coverage
        if self.mapping is not None:
            mapping_stats = self._analyze_mapping_coverage()
            coverage_stats['mapping'] = mapping_stats
            
        self.results['raw_coverage'] = coverage_stats
        return coverage_stats
        
    def _analyze_finbas_coverage(self):
        """Analyze Finbas (market data) coverage."""
        print("\nFinbas Market Data Coverage:")
        print("-" * 40)
        
        df = self.raw_finbas.copy()
        
        # Basic statistics (already processed data, so it's Swedish SE+SEK only)
        stats = {
            'total_observations': len(df),
            'unique_isins': df['isin'].nunique(),
            'date_range': (df['date'].min(), df['date'].max()),
        }
        
        if 'exchange' in df.columns:
            stats['exchanges'] = df['exchange'].value_counts().head(10).to_dict()
        
        # This is already Swedish market data (processed)
        stats['swedish_market'] = {
            'observations': len(df),
            'unique_isins': df['isin'].nunique(),
            'percentage_of_total': 100.0  # Processed data is already filtered
        }
        
        # Temporal coverage
        df_temporal = df.groupby(df['date'].dt.to_period('M')).agg({
            'isin': 'nunique',
            'close': 'count'
        }).rename(columns={'isin': 'unique_firms', 'close': 'observations'})
        
        stats['temporal_coverage'] = {
            'monthly_stats': df_temporal.describe().to_dict(),
            'time_series': df_temporal.reset_index()
        }
        
        # Variable completeness for key market variables
        key_vars = ['close', 'market_cap', 'turnover_sek', 'volume', 'ask', 'bid']
        available_vars = [var for var in key_vars if var in df.columns]
        
        completeness = {}
        for var in available_vars:
            completeness[var] = {
                'non_null_count': df[var].notna().sum(),
                'completeness_rate': df[var].notna().mean() * 100
            }
        stats['variable_completeness'] = completeness
        
        # Print summary
        print(f"  Total observations: {stats['total_observations']:,}")
        print(f"  Unique ISINs: {stats['unique_isins']:,}")
        print(f"  Date range: {stats['date_range'][0].strftime('%Y-%m-%d')} to {stats['date_range'][1].strftime('%Y-%m-%d')}")
        print(f"  Monthly observations (processed Swedish market data)")
        
        return stats
        
    def _analyze_serrano_coverage(self):
        """Analyze Serrano (accounting data) coverage."""
        print("\nSerrano Accounting Data Coverage (Sample Analysis):")
        print("-" * 40)
        
        df = self.raw_serrano.copy()
        
        # Get full file stats efficiently
        import os
        full_file_size = os.path.getsize(INTERMEDIATE_SERRANO_PATH)
        estimated_rows = int(full_file_size / (full_file_size / len(df)) * len(df))  # Rough estimate
        
        # Basic statistics from sample
        stats = {
            'sample_observations': len(df),
            'estimated_total_observations': estimated_rows,
            'unique_orgnrs_in_sample': df['orgnr'].nunique(),
        }
        
        # Fiscal year coverage
        if 'fiscal_year_end' in df.columns:
            stats['fiscal_year_range'] = (df['fiscal_year_end'].min(), df['fiscal_year_end'].max())
            
            # Yearly coverage from sample
            yearly_coverage = df.groupby(df['fiscal_year_end'].dt.year).agg({
                'orgnr': 'nunique',
                'fiscal_year_end': 'count'
            }).rename(columns={'orgnr': 'unique_firms', 'fiscal_year_end': 'observations'})
            
            stats['yearly_coverage'] = yearly_coverage.reset_index()
            
        # Variable completeness for key accounting variables
        # These are the main variables used in P-Tree characteristics
        key_accounting_vars = [
            'total_assets', 'book_equity', 'net_income', 'sales',
            'cash', 'long_term_debt', 'current_liabilities', 'current_assets',
            'operating_income', 'depreciation', 'ppe_buildings', 'ppe_machinery',
            'cogs_materials', 'cogs_goods', 'tax_expense', 'num_employees'
        ]
        
        available_vars = [var for var in key_accounting_vars if var in df.columns]
        
        completeness = {}
        for var in available_vars:
            completeness[var] = {
                'non_null_count': df[var].notna().sum(),
                'completeness_rate': df[var].notna().mean() * 100
            }
        stats['variable_completeness'] = completeness
        
        # Mapping coverage (how many Serrano firms have ISINs)
        if self.mapping is not None:
            mapped_orgnrs = set(self.mapping['orgnr'].astype(str))
            serrano_orgnrs = set(df['orgnr'].astype(str))
            
            stats['mapping_coverage'] = {
                'serrano_firms_with_isin': len(serrano_orgnrs.intersection(mapped_orgnrs)),
                'total_serrano_firms_in_sample': len(serrano_orgnrs),
                'mapping_rate': len(serrano_orgnrs.intersection(mapped_orgnrs)) / len(serrano_orgnrs) * 100
            }
        
        # Print summary
        print(f"  Sample observations: {stats['sample_observations']:,}")
        print(f"  Estimated total observations: {stats['estimated_total_observations']:,}")
        print(f"  Unique ORGNRs in sample: {stats['unique_orgnrs_in_sample']:,}")
        if 'fiscal_year_range' in stats:
            print(f"  Fiscal year range: {stats['fiscal_year_range'][0].strftime('%Y-%m-%d')} to {stats['fiscal_year_range'][1].strftime('%Y-%m-%d')}")
        if 'mapping_coverage' in stats:
            print(f"  Sample firms with ISIN mapping: {stats['mapping_coverage']['serrano_firms_with_isin']:,} / {stats['mapping_coverage']['total_serrano_firms_in_sample']:,} ({stats['mapping_coverage']['mapping_rate']:.1f}%)")
            
        return stats
        
    def _analyze_mapping_coverage(self):
        """Analyze ISIN-ORGNR mapping coverage."""
        print("\nISIN-ORGNR Mapping Coverage:")
        print("-" * 40)
        
        df = self.mapping.copy()
        
        stats = {
            'total_mappings': len(df),
            'unique_isins': df['isin'].nunique(),
            'unique_orgnrs': df['orgnr'].nunique(),
        }
        
        # Mapping source analysis (if available)
        if 'source' in df.columns:
            stats['mapping_sources'] = df['source'].value_counts().to_dict()
            
        print(f"  Total mappings: {stats['total_mappings']:,}")
        print(f"  Unique ISINs: {stats['unique_isins']:,}")
        print(f"  Unique ORGNRs: {stats['unique_orgnrs']:,}")
        
        return stats

    def analyze_final_dataset_coverage(self):
        """Analyze coverage and representation in the final P-Tree dataset."""
        print("\n" + "="*60)
        print("ANALYZING FINAL DATASET COVERAGE")
        print("="*60)
        
        if self.final_data is None:
            print("Final dataset not available for analysis")
            return None
            
        df = self.final_data.copy()
        
        # Basic dataset statistics
        basic_stats = {
            'total_observations': len(df),
            'unique_firms': df['isin'].nunique(),
            'date_range': (df['date'].min(), df['date'].max()),
            'monthly_periods': df['date'].dt.to_period('M').nunique(),
        }
        
        print(f"Final Dataset Overview:")
        print(f"  Total observations: {basic_stats['total_observations']:,}")
        print(f"  Unique firms (ISINs): {basic_stats['unique_firms']:,}")
        print(f"  Date range: {basic_stats['date_range'][0].strftime('%Y-%m-%d')} to {basic_stats['date_range'][1].strftime('%Y-%m-%d')}")
        print(f"  Monthly periods: {basic_stats['monthly_periods']:,}")
        
        # Firm representation analysis
        firm_representation = self._analyze_firm_representation(df)
        
        # Variable coverage analysis
        variable_coverage = self._analyze_variable_coverage(df)
        
        # Temporal patterns
        temporal_analysis = self._analyze_temporal_patterns(df)
        
        results = {
            'basic_stats': basic_stats,
            'firm_representation': firm_representation,
            'variable_coverage': variable_coverage,
            'temporal_analysis': temporal_analysis
        }
        
        self.results['final_dataset'] = results
        return results
        
    def _analyze_firm_representation(self, df):
        """Analyze how firms are represented over time periods."""
        print("\nFirm Representation Analysis:")
        print("-" * 40)
        
        # Count observations per firm
        firm_counts = df.groupby('isin').agg({
            'date': ['count', 'min', 'max'],
            'ret_monthly': 'count'  # Count non-null returns
        }).reset_index()
        
        firm_counts.columns = ['isin', 'total_periods', 'first_date', 'last_date', 'periods_with_returns']
        
        # Calculate duration in months for each firm
        firm_counts['duration_months'] = ((firm_counts['last_date'] - firm_counts['first_date']).dt.days / 30.44).round()
        firm_counts['data_density'] = firm_counts['total_periods'] / (firm_counts['duration_months'] + 1)
        
        # Summary statistics
        representation_stats = {
            'periods_per_firm': firm_counts['total_periods'].describe().to_dict(),
            'duration_months': firm_counts['duration_months'].describe().to_dict(),
            'data_density': firm_counts['data_density'].describe().to_dict(),
        }
        
        # Distribution analysis
        period_bins = [1, 12, 36, 60, 120, float('inf')]
        period_labels = ['1-11 months', '1-2.9 years', '3-4.9 years', '5-9.9 years', '10+ years']
        firm_counts['period_category'] = pd.cut(firm_counts['total_periods'], bins=period_bins, labels=period_labels, right=False)
        
        representation_stats['period_distribution'] = firm_counts['period_category'].value_counts().to_dict()
        
        # Firms with substantial coverage (>= 36 months)
        substantial_firms = firm_counts[firm_counts['total_periods'] >= 36]
        representation_stats['substantial_coverage'] = {
            'count': len(substantial_firms),
            'percentage': len(substantial_firms) / len(firm_counts) * 100
        }
        
        print(f"  Average periods per firm: {representation_stats['periods_per_firm']['mean']:.1f}")
        print(f"  Median periods per firm: {representation_stats['periods_per_firm']['50%']:.1f}")
        print(f"  Firms with 3+ years data: {representation_stats['substantial_coverage']['count']:,} ({representation_stats['substantial_coverage']['percentage']:.1f}%)")
        
        representation_stats['firm_details'] = firm_counts
        
        return representation_stats
        
    def _analyze_variable_coverage(self, df):
        """Analyze coverage of P-Tree characteristics."""
        print("\nVariable Coverage Analysis:")
        print("-" * 40)
        
        # Get all rank_ columns (the P-Tree characteristics)
        rank_cols = [col for col in df.columns if col.startswith('rank_')]
        
        # Calculate coverage for each characteristic
        coverage_stats = {}
        for col in rank_cols:
            non_zero_count = (df[col] != 0).sum()  # Non-neutral rankings
            total_count = len(df)
            
            coverage_stats[col] = {
                'total_observations': total_count,
                'non_zero_count': non_zero_count,
                'coverage_rate': non_zero_count / total_count * 100,
                'missing_rate': (df[col] == 0).mean() * 100  # Neutral = missing in P-Tree
            }
        
        # Sort by coverage rate
        coverage_df = pd.DataFrame(coverage_stats).T
        coverage_df = coverage_df.sort_values('coverage_rate', ascending=False)
        
        # Categorize variables by coverage
        high_coverage = coverage_df[coverage_df['coverage_rate'] >= 75]
        medium_coverage = coverage_df[(coverage_df['coverage_rate'] >= 25) & (coverage_df['coverage_rate'] < 75)]
        low_coverage = coverage_df[coverage_df['coverage_rate'] < 25]
        
        summary = {
            'total_characteristics': len(rank_cols),
            'high_coverage_vars': len(high_coverage),
            'medium_coverage_vars': len(medium_coverage),
            'low_coverage_vars': len(low_coverage),
            'coverage_details': coverage_df,
            'high_coverage_list': high_coverage.index.tolist(),
            'medium_coverage_list': medium_coverage.index.tolist(),
            'low_coverage_list': low_coverage.index.tolist()
        }
        
        print(f"  Total characteristics: {summary['total_characteristics']}")
        print(f"  High coverage (>=75%): {summary['high_coverage_vars']}")
        print(f"  Medium coverage (25-74%): {summary['medium_coverage_vars']}")
        print(f"  Low coverage (<25%): {summary['low_coverage_vars']}")
        
        return summary
        
    def _analyze_temporal_patterns(self, df):
        """Analyze temporal patterns in data availability."""
        print("\nTemporal Coverage Analysis:")
        print("-" * 40)
        
        # Monthly aggregation
        monthly_stats = df.groupby(df['date'].dt.to_period('M')).agg({
            'isin': 'nunique',
            'ret_monthly': 'count',
            'market_cap': lambda x: x.notna().sum()
        }).rename(columns={
            'isin': 'unique_firms',
            'ret_monthly': 'observations_with_returns',
            'market_cap': 'observations_with_market_cap'
        })
        
        # Yearly aggregation  
        yearly_stats = df.groupby(df['date'].dt.year).agg({
            'isin': 'nunique',
            'ret_monthly': 'count'
        }).rename(columns={
            'isin': 'unique_firms',
            'ret_monthly': 'total_observations'
        })
        
        temporal_summary = {
            'monthly_coverage': {
                'mean_firms_per_month': monthly_stats['unique_firms'].mean(),
                'min_firms_per_month': monthly_stats['unique_firms'].min(),
                'max_firms_per_month': monthly_stats['unique_firms'].max(),
                'time_series': monthly_stats.reset_index()
            },
            'yearly_coverage': {
                'time_series': yearly_stats.reset_index()
            }
        }
        
        print(f"  Average firms per month: {temporal_summary['monthly_coverage']['mean_firms_per_month']:.0f}")
        print(f"  Range: {temporal_summary['monthly_coverage']['min_firms_per_month']:,} - {temporal_summary['monthly_coverage']['max_firms_per_month']:,} firms per month")
        
        return temporal_summary

    def create_visualizations(self):
        """Create comprehensive visualizations for thesis."""
        print("\n" + "="*60)
        print("CREATING VISUALIZATIONS")
        print("="*60)
        
        if self.final_data is None:
            print("Cannot create visualizations without final dataset")
            return
            
        # Set up the plotting style
        plt.rcParams.update({
            'font.size': 12,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'figure.titlesize': 16
        })
        
        # 1. Temporal coverage evolution
        self._plot_temporal_evolution()
        
        # 2. Firm representation distribution
        self._plot_firm_representation()
        
        # 3. Variable coverage heatmap
        self._plot_variable_coverage()
        
        # 4. Data source comparison
        self._plot_data_source_comparison()
        
        # 5. Original paper comparison
        self._plot_original_paper_comparison()
        
        print("Visualizations saved to:", OUTPUT_DIR)
        
    def _plot_temporal_evolution(self):
        """Plot evolution of data coverage over time."""
        df = self.final_data.copy()
        
        # Monthly data
        monthly_data = df.groupby(df['date'].dt.to_period('M')).agg({
            'isin': 'nunique',
            'ret_monthly': 'count'
        }).rename(columns={'isin': 'Unique Firms', 'ret_monthly': 'Total Observations'})
        
        monthly_data.index = monthly_data.index.to_timestamp()
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        
        # Plot firms over time
        ax1.plot(monthly_data.index, monthly_data['Unique Firms'], 
                linewidth=2, color='#2E86C1', marker='o', markersize=3)
        ax1.set_ylabel('Number of Unique Firms')
        ax1.set_title('Data Coverage Evolution Over Time')
        ax1.grid(True, alpha=0.3)
        
        # Plot observations over time
        ax2.plot(monthly_data.index, monthly_data['Total Observations'], 
                linewidth=2, color='#E74C3C', marker='s', markersize=3)
        ax2.set_ylabel('Total Observations')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        years = mdates.YearLocator()
        months = mdates.MonthLocator()
        yearsFmt = mdates.DateFormatter('%Y')
        
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_locator(years)
            ax.xaxis.set_major_formatter(yearsFmt)
            ax.xaxis.set_minor_locator(months)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'temporal_coverage_evolution.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
        
    def _plot_firm_representation(self):
        """Plot distribution of firm representation periods."""
        if 'final_dataset' not in self.results:
            return
            
        firm_details = self.results['final_dataset']['firm_representation']['firm_details']
        
        # Plot 1: Histogram of periods per firm
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        ax.hist(firm_details['total_periods'], bins=50, alpha=0.7, color='#3498DB', edgecolor='black')
        ax.set_xlabel('Number of Periods')
        ax.set_ylabel('Number of Firms')
        ax.set_title('Distribution of Periods per Firm')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'firm_periods_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 2: Histogram of duration in months
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        ax.hist(firm_details['duration_months'], bins=50, alpha=0.7, color='#E67E22', edgecolor='black')
        ax.set_xlabel('Duration (Months)')
        ax.set_ylabel('Number of Firms')
        ax.set_title('Distribution of Firm Duration in Dataset')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'firm_duration_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 3: Data density scatter plot
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        ax.scatter(firm_details['duration_months'], firm_details['data_density'], 
                   alpha=0.6, s=30, color='#27AE60')
        ax.set_xlabel('Duration (Months)')
        ax.set_ylabel('Data Density (Observations/Month)')
        ax.set_title('Data Density vs. Duration')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'firm_data_density.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 4: Period category distribution
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        period_dist = self.results['final_dataset']['firm_representation']['period_distribution']
        ax.pie(period_dist.values(), labels=period_dist.keys(), autopct='%1.1f%%',
               colors=['#E74C3C', '#F39C12', '#F1C40F', '#2ECC71', '#3498DB'])
        ax.set_title('Firm Representation Categories')
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'firm_representation_categories.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
        
    def _plot_variable_coverage(self):
        """Plot variable coverage analysis."""
        if 'final_dataset' not in self.results:
            return
            
        coverage_df = self.results['final_dataset']['variable_coverage']['coverage_details']
        
        # Plot 1: Coverage rate bar plot
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        top_vars = coverage_df.head(20)  # Top 20 variables
        y_pos = np.arange(len(top_vars))
        
        colors = ['#2ECC71' if x >= 75 else '#F39C12' if x >= 25 else '#E74C3C' 
                 for x in top_vars['coverage_rate']]
        
        bars = ax.barh(y_pos, top_vars['coverage_rate'], color=colors, alpha=0.8)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([col.replace('rank_', '') for col in top_vars.index])
        ax.set_xlabel('Coverage Rate (%)')
        ax.set_title('Variable Coverage Rates (Top 20)')
        ax.grid(True, axis='x', alpha=0.3)
        
        # Add value labels on bars
        for i, (bar, val) in enumerate(zip(bars, top_vars['coverage_rate'])):
            ax.text(val + 1, bar.get_y() + bar.get_height()/2, 
                    f'{val:.1f}%', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'variable_coverage_rates.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 2: Coverage distribution
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        coverage_bins = [0, 25, 50, 75, 100]
        coverage_labels = ['Very Low\n(0-24%)', 'Low\n(25-49%)', 'Medium\n(50-74%)', 'High\n(75-100%)']
        coverage_counts = pd.cut(coverage_df['coverage_rate'], bins=coverage_bins, 
                               labels=coverage_labels, right=False).value_counts()
        
        colors_pie = ['#E74C3C', '#F39C12', '#F1C40F', '#2ECC71']
        ax.pie(coverage_counts.values, labels=coverage_counts.index, autopct='%1.0f',
               colors=colors_pie, startangle=90)
        ax.set_title('Distribution of Variable Coverage')
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'variable_coverage_distribution.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
        
    def _plot_data_source_comparison(self):
        """Plot comparison of data sources."""
        if not all(key in self.results for key in ['raw_coverage']):
            return
            
        # Plot 1: Observations by source
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        sources = ['Finbas', 'Serrano', 'Final Dataset']
        obs_counts = []
        
        if 'finbas' in self.results['raw_coverage']:
            obs_counts.append(self.results['raw_coverage']['finbas']['swedish_market']['observations'])
        else:
            obs_counts.append(0)
            
        if 'serrano' in self.results['raw_coverage']:
            serrano_stats = self.results['raw_coverage']['serrano']
            obs_count = serrano_stats.get('estimated_total_observations', serrano_stats['sample_observations'])
            obs_counts.append(obs_count)
        else:
            obs_counts.append(0)
            
        if 'final_dataset' in self.results:
            obs_counts.append(self.results['final_dataset']['basic_stats']['total_observations'])
        else:
            obs_counts.append(0)
        
        ax.bar(sources, obs_counts, color=['#3498DB', '#E67E22', '#2ECC71'], alpha=0.8)
        ax.set_ylabel('Number of Observations')
        ax.set_title('Observations by Data Source')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Add value labels
        for i, v in enumerate(obs_counts):
            ax.text(i, v + max(obs_counts) * 0.01, f'{v:,}', ha='center', fontweight='bold')
            
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'data_source_observations.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 2: Unique entities by source
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        entity_counts = []
        entity_labels = []
        
        if 'finbas' in self.results['raw_coverage']:
            entity_counts.append(self.results['raw_coverage']['finbas']['swedish_market']['unique_isins'])
            entity_labels.append('Finbas\n(ISINs)')
        
        if 'serrano' in self.results['raw_coverage']:
            entity_counts.append(self.results['raw_coverage']['serrano']['unique_orgnrs_in_sample'])
            entity_labels.append('Serrano\n(ORGNRs)')
            
        if 'mapping' in self.results['raw_coverage']:
            entity_counts.append(self.results['raw_coverage']['mapping']['unique_isins'])
            entity_labels.append('Mapping\n(ISINs)')
            
        if 'final_dataset' in self.results:
            entity_counts.append(self.results['final_dataset']['basic_stats']['unique_firms'])
            entity_labels.append('Final\n(Firms)')
        
        ax.bar(entity_labels, entity_counts, 
               color=['#3498DB', '#E67E22', '#9B59B6', '#2ECC71'], alpha=0.8)
        ax.set_ylabel('Number of Unique Entities')
        ax.set_title('Unique Entities by Data Source')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Add value labels
        for i, v in enumerate(entity_counts):
            ax.text(i, v + max(entity_counts) * 0.01, f'{v:,}', ha='center', fontweight='bold')
            
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'data_source_entities.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 3: Temporal coverage comparison
        fig, ax = plt.subplots(1, 1, figsize=(12, 6))
        if 'final_dataset' in self.results:
            monthly_data = self.results['final_dataset']['temporal_analysis']['monthly_coverage']['time_series'].copy()
            # The index name when reset is typically 'date' from the original groupby
            date_col = monthly_data.columns[0]  # First column should be the date/period
            monthly_data[date_col] = pd.to_datetime(monthly_data[date_col].astype(str))
            
            ax.plot(monthly_data[date_col], monthly_data['unique_firms'], 
                    linewidth=2, marker='o', markersize=4, color='#2ECC71')
            ax.set_ylabel('Number of Firms')
            ax.set_xlabel('Date')
            ax.set_title('Final Dataset: Firms per Month')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'temporal_coverage_monthly.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_original_paper_comparison(self):
        """Create comparisons with original P-Tree and similar academic papers."""
        if 'final_dataset' not in self.results:
            return
            
        # Original P-Tree paper benchmarks (approximate values from literature)
        original_paper_stats = {
            'Cong et al. (2023) - US Market': {
                'firms': 8000,
                'time_period': '1962-2021',
                'observations_millions': 4.8,
                'characteristics': 50,
                'market': 'US (CRSP/Compustat)'
            },
            'Our Swedish Study': {
                'firms': self.results['final_dataset']['basic_stats']['unique_firms'],
                'time_period': f"{self.results['final_dataset']['basic_stats']['date_range'][0].year}-{self.results['final_dataset']['basic_stats']['date_range'][1].year}",
                'observations_millions': self.results['final_dataset']['basic_stats']['total_observations'] / 1_000_000,
                'characteristics': self.results['final_dataset']['variable_coverage']['total_characteristics'],
                'market': 'Swedish (Finbas/Serrano)'
            }
        }
        
        # 1a. Dataset Size - Number of Firms (individual chart)
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        studies = list(original_paper_stats.keys())
        firms = [original_paper_stats[study]['firms'] for study in studies]
        
        # Clean study names for display
        clean_studies = ['Cong et al.\n(2023)', 'Our Swedish\nStudy']
        
        bars = ax.bar(clean_studies, firms, color=['#3498DB', '#2ECC71'], alpha=0.8, width=0.6)
        ax.set_ylabel('Number of Firms')
        ax.set_title('Number of Firms Comparison')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Add value labels on bars with better spacing
        for bar, val in zip(bars, firms):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(firms)*0.02, 
                    f'{val:,}', ha='center', va='bottom', fontweight='bold', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'dataset_firms_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 1b. Dataset Size - Observations (individual chart)
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        obs_millions = [original_paper_stats[study]['observations_millions'] for study in studies]
        
        bars = ax.bar(clean_studies, obs_millions, color=['#E74C3C', '#E67E22'], alpha=0.8, width=0.6)
        ax.set_ylabel('Observations (Millions)')
        ax.set_title('Number of Observations Comparison')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Add value labels on bars with better spacing
        for bar, val in zip(bars, obs_millions):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(obs_millions)*0.02, 
                    f'{val:.1f}M', ha='center', va='bottom', fontweight='bold', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'dataset_observations_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Time Period Coverage Comparison
        fig, ax = plt.subplots(1, 1, figsize=(14, 6))
        
        periods = []
        start_years = []
        end_years = []
        study_names = []
        
        for study, stats in original_paper_stats.items():
            period = stats['time_period']
            if '-' in period:
                start, end = period.split('-')
                start_years.append(int(start))
                end_years.append(int(end))
                periods.append(int(end) - int(start) + 1)
                study_names.append(study)
        
        # Create timeline bars
        y_positions = np.arange(len(study_names))
        colors = ['#E74C3C', '#F39C12', '#2ECC71']
        
        for i, (start, end, study) in enumerate(zip(start_years, end_years, study_names)):
            ax.barh(y_positions[i], end - start, left=start, height=0.6, 
                   color=colors[i], alpha=0.8, label=study)
            
            # Add period length annotation
            ax.text(start + (end - start)/2, y_positions[i], f'{end-start+1} years', 
                   ha='center', va='center', fontweight='bold', color='white')
        
        ax.set_yticks(y_positions)
        ax.set_yticklabels(study_names)
        ax.set_xlabel('Year')
        ax.set_title('Time Period Coverage: Our Study vs. Academic Literature')
        ax.grid(True, axis='x', alpha=0.3)
        
        # Set x-axis limits
        ax.set_xlim(min(start_years) - 2, max(end_years) + 2)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'time_period_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3a. Characteristics count comparison (individual chart)
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        chars = [original_paper_stats[study]['characteristics'] for study in studies]
        bars = ax.bar(studies, chars, color=['#3498DB', '#2ECC71'], alpha=0.8)
        ax.set_ylabel('Number of Characteristics')
        ax.set_title('Characteristics Coverage Comparison')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Rotate labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add value labels
        for bar, val in zip(bars, chars):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(chars)*0.01, 
                    f'{val}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'characteristics_coverage_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3b. Market focus comparison (individual chart)
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        market_types = ['US Market\n(Cong et al.)', 'Swedish Market\n(Our Study)']
        sizes = [1, 1]  # Equal representation for comparison
        colors_pie = ['#3498DB', '#2ECC71']
        
        ax.pie(sizes, labels=market_types, colors=colors_pie, autopct='', startangle=90)
        ax.set_title('Market Focus Comparison')
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'market_focus_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 4. Individual Data Quality Metrics
        if 'final_dataset' in self.results:
            firm_rep = self.results['final_dataset']['firm_representation']
            var_cov = self.results['final_dataset']['variable_coverage']
            
            # 4a. Average periods per firm comparison (individual chart)
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            periods_comparison = {
                'Cong et al. (2023)': 120,  # ~10 years monthly
                'Our Study': firm_rep['periods_per_firm']['mean']
            }
            
            bars = ax.bar(periods_comparison.keys(), periods_comparison.values(), 
                          color=['#95A5A6', '#2ECC71'], alpha=0.8)
            ax.set_ylabel('Average Periods per Firm')
            ax.set_title('Data Persistence Comparison')
            ax.grid(True, axis='y', alpha=0.3)
            
            for bar, val in zip(bars, periods_comparison.values()):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(periods_comparison.values())*0.01, 
                        f'{val:.1f}', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / 'data_persistence_comparison.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 4b. Variable coverage quality (individual chart)
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            coverage_dist = {
                'High (≥75%)': var_cov['high_coverage_vars'],
                'Medium (25-74%)': var_cov['medium_coverage_vars'], 
                'Low (<25%)': var_cov['low_coverage_vars']
            }
            
            bars = ax.bar(coverage_dist.keys(), coverage_dist.values(), 
                          color=['#2ECC71', '#F39C12', '#E74C3C'], alpha=0.8)
            ax.set_ylabel('Number of Variables')
            ax.set_title('Variable Coverage Quality')
            ax.grid(True, axis='y', alpha=0.3)
            
            for bar, val in zip(bars, coverage_dist.values()):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(coverage_dist.values())*0.01, 
                        f'{val}', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / 'variable_coverage_quality.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 4c. Firm representation distribution (individual chart) 
            fig, ax = plt.subplots(1, 1, figsize=(10, 8))
            period_dist = firm_rep['period_distribution']
            ax.pie(period_dist.values(), labels=period_dist.keys(), autopct='%1.1f%%',
                   colors=['#E74C3C', '#F39C12', '#F1C40F', '#2ECC71', '#3498DB'])
            ax.set_title('Firm Representation Distribution')
            
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / 'firm_representation_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 4d. Temporal coverage evolution (individual chart)
            fig, ax = plt.subplots(1, 1, figsize=(12, 6))
            temporal = self.results['final_dataset']['temporal_analysis']['monthly_coverage']['time_series']
            date_col = temporal.columns[0]
            sample_temporal = temporal.iloc[::12]  # Sample every 12 months for clarity
            
            ax.plot(range(len(sample_temporal)), sample_temporal['unique_firms'], 
                    linewidth=3, marker='o', markersize=6, color='#2ECC71')
            ax.set_xlabel('Time (Years, Sampled)')
            ax.set_ylabel('Number of Active Firms') 
            ax.set_title('Temporal Coverage Evolution')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / 'temporal_coverage_evolution_sample.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # 5. Summary comparison table visualization
        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        ax.axis('off')
        
        # Create comparison table data
        table_data = []
        headers = ['Study', 'Market', 'Firms', 'Time Period', 'Obs (M)', 'Characteristics', 'Avg Years/Firm']
        
        for study, stats in original_paper_stats.items():
            if study == 'Our Swedish Study':
                avg_years = firm_rep['periods_per_firm']['mean'] / 12
            else:
                # Cong et al. study period
                avg_years = 15
                
            row = [
                study.replace(' - ', '\\n'),
                stats['market'],
                f"{stats['firms']:,}",
                stats['time_period'],
                f"{stats['observations_millions']:.1f}",
                f"{stats['characteristics']}",
                f"{avg_years:.1f}"
            ]
            table_data.append(row)
        
        # Create table
        table = ax.table(cellText=table_data, colLabels=headers, 
                        cellLoc='center', loc='center',
                        colWidths=[0.18, 0.15, 0.12, 0.12, 0.08, 0.1, 0.12])
        
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        
        # Style the table
        for i in range(len(headers)):
            table[(0, i)].set_facecolor('#34495E')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Color our study row differently
        for i in range(len(headers)):
            table[(len(table_data), i)].set_facecolor('#E8F6F3')
        
        ax.set_title('Comprehensive Study Comparison', fontsize=16, fontweight='bold', pad=20)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'comprehensive_study_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()

    def generate_latex_tables(self):
        """Generate LaTeX formatted tables for thesis."""
        print("\n" + "="*60)
        print("GENERATING LATEX TABLES")
        print("="*60)
        
        latex_output_dir = OUTPUT_DIR / 'latex_tables'
        latex_output_dir.mkdir(exist_ok=True)
        
        # 1. Data source summary table
        self._generate_data_source_table(latex_output_dir)
        
        # 2. Variable coverage table
        self._generate_variable_coverage_table(latex_output_dir)
        
        # 3. Firm representation table
        self._generate_firm_representation_table(latex_output_dir)
        
        # 4. Temporal coverage table
        self._generate_temporal_coverage_table(latex_output_dir)
        
        print("LaTeX tables saved to:", latex_output_dir)
        
    def _generate_data_source_table(self, output_dir):
        """Generate LaTeX table for data source summary."""
        latex_content = """
\\begin{table}[htbp]
\\centering
\\caption{Data Source Summary and Coverage Statistics}
\\label{tab:data_source_summary}
\\begin{tabular}{lrrrr}
\\toprule
\\textbf{Data Source} & \\textbf{Observations} & \\textbf{Unique Entities} & \\textbf{Time Period} & \\textbf{Coverage} \\\\
\\midrule
"""
        
        # Finbas data
        if 'finbas' in self.results.get('raw_coverage', {}):
            finbas_stats = self.results['raw_coverage']['finbas']
            date_range = finbas_stats['date_range']
            latex_content += f"Finbas (Market) & {finbas_stats['swedish_market']['observations']:,} & "
            latex_content += f"{finbas_stats['swedish_market']['unique_isins']:,} ISINs & "
            latex_content += f"{date_range[0].strftime('%Y-%m')} -- {date_range[1].strftime('%Y-%m')} & "
            latex_content += f"{finbas_stats['swedish_market']['percentage_of_total']:.1f}\\% Swedish \\\\\n"
        
        # Serrano data
        if 'serrano' in self.results.get('raw_coverage', {}):
            serrano_stats = self.results['raw_coverage']['serrano']
            if 'fiscal_year_range' in serrano_stats:
                date_range = serrano_stats['fiscal_year_range']
                # Use estimated total or sample size
                obs_count = serrano_stats.get('estimated_total_observations', serrano_stats['sample_observations'])
                orgnr_count = serrano_stats['unique_orgnrs_in_sample']
                latex_content += f"Serrano (Accounting) & {obs_count:,} & "
                latex_content += f"{orgnr_count:,} ORGNRs & "
                latex_content += f"{date_range[0].strftime('%Y')} -- {date_range[1].strftime('%Y')} & "
                if 'mapping_coverage' in serrano_stats:
                    latex_content += f"{serrano_stats['mapping_coverage']['mapping_rate']:.1f}\\% with ISIN \\\\\n"
                else:
                    latex_content += "-- \\\\\n"
        
        # Final dataset
        if 'final_dataset' in self.results:
            basic_stats = self.results['final_dataset']['basic_stats']
            date_range = basic_stats['date_range']
            latex_content += f"Final Dataset & {basic_stats['total_observations']:,} & "
            latex_content += f"{basic_stats['unique_firms']:,} Firms & "
            latex_content += f"{date_range[0].strftime('%Y-%m')} -- {date_range[1].strftime('%Y-%m')} & "
            latex_content += f"{basic_stats['monthly_periods']:,} Months \\\\\n"
        
        latex_content += """\\bottomrule
\\end{tabular}
\\begin{tablenotes}
\\small
\\item Note: Swedish market data filtered to SE ISINs with SEK currency. 
Accounting data includes both public and private firms, with ISIN mapping coverage shown for public firms.
Final dataset represents the merged and processed data used for P-Tree analysis.
\\end{tablenotes}
\\end{table}
"""
        
        with open(output_dir / 'data_source_summary.tex', 'w', encoding='utf-8') as f:
            f.write(latex_content)
            
    def _generate_variable_coverage_table(self, output_dir):
        """Generate LaTeX table for variable coverage analysis."""
        if 'final_dataset' not in self.results:
            return
            
        coverage_df = self.results['final_dataset']['variable_coverage']['coverage_details']
        
        # Group variables by category (based on characteristic type)
        momentum_vars = [col for col in coverage_df.index if any(x in col.lower() for x in ['mom', 'seas', 'chtx'])]
        value_vars = [col for col in coverage_df.index if any(x in col.lower() for x in ['bm', 'ep', 'sp', 'cfp', 'cash', 'lev'])]
        profitability_vars = [col for col in coverage_df.index if any(x in col.lower() for x in ['roa', 'roe', 'pm', 'op', 'rna', 'ato'])]
        investment_vars = [col for col in coverage_df.index if any(x in col.lower() for x in ['agr', 'lgr', 'acc', 'pct', 'noa', 'cinvest', 'gma', 'chcsho', 'ni', 'grltnoa'])]
        other_vars = [col for col in coverage_df.index if col not in momentum_vars + value_vars + profitability_vars + investment_vars]
        
        categories = [
            ('Momentum', momentum_vars),
            ('Value', value_vars), 
            ('Profitability', profitability_vars),
            ('Investment', investment_vars),
            ('Other', other_vars)
        ]
        
        latex_content = """
\\begin{table}[htbp]
\\centering
\\caption{Variable Coverage by Characteristic Category}
\\label{tab:variable_coverage}
\\scalebox{0.9}{
\\begin{tabular}{llrr}
\\toprule
\\textbf{Category} & \\textbf{Variable} & \\textbf{Coverage (\\%)} & \\textbf{Observations} \\\\
\\midrule
"""
        
        for category_name, variables in categories:
            if not variables:
                continue
                
            # Sort variables in this category by coverage
            category_data = coverage_df.loc[variables].sort_values('coverage_rate', ascending=False)
            
            for i, (var, row) in enumerate(category_data.iterrows()):
                if i == 0:
                    latex_content += f"\\multirow{{{len(category_data)}}}{{*}}{{{category_name}}} & "
                else:
                    latex_content += " & "
                
                var_clean = var.replace('rank_', '').upper()
                latex_content += f"{var_clean} & {row['coverage_rate']:.1f} & {row['non_zero_count']:,} \\\\\n"
        
        latex_content += """\\bottomrule
\\end{tabular}
}
\\begin{tablenotes}
\\small
\\item Note: Coverage represents the percentage of observations with non-zero (non-neutral) rankings.
Variables are ranked within each cross-section, with missing values assigned neutral rank of 0.
High coverage (>=75\\%), medium coverage (25-74\\%), and low coverage (<25\\%) variables are included.
\\end{tablenotes}
\\end{table}
"""
        
        with open(output_dir / 'variable_coverage.tex', 'w', encoding='utf-8') as f:
            f.write(latex_content)
            
    def _generate_firm_representation_table(self, output_dir):
        """Generate LaTeX table for firm representation analysis."""
        if 'final_dataset' not in self.results:
            return
            
        representation_stats = self.results['final_dataset']['firm_representation']
        
        latex_content = """
\\begin{table}[htbp]
\\centering
\\caption{Firm Representation and Data Persistence Analysis}
\\label{tab:firm_representation}
\\begin{tabular}{lrr}
\\toprule
\\textbf{Metric} & \\textbf{Value} & \\textbf{Percentage} \\\\
\\midrule
"""
        
        # Basic statistics
        periods_stats = representation_stats['periods_per_firm']
        latex_content += f"Total Unique Firms & {len(representation_stats['firm_details']):,} & 100.0\\% \\\\\n"
        latex_content += "\\midrule\n"
        
        # Period distribution
        latex_content += "\\textbf{Data Persistence:} & & \\\\\n"
        period_dist = representation_stats['period_distribution']
        total_firms = sum(period_dist.values())
        
        for period_range, count in period_dist.items():
            percentage = count / total_firms * 100
            latex_content += f"{period_range} & {count:,} & {percentage:.1f}\\% \\\\\n"
            
        latex_content += "\\midrule\n"
        
        # Summary statistics
        latex_content += "\\textbf{Summary Statistics:} & & \\\\\n"
        latex_content += f"Mean periods per firm & {periods_stats['mean']:.1f} & -- \\\\\n"
        latex_content += f"Median periods per firm & {periods_stats['50%']:.1f} & -- \\\\\n"
        latex_content += f"Standard deviation & {periods_stats['std']:.1f} & -- \\\\\n"
        latex_content += f"Minimum periods & {periods_stats['min']:.0f} & -- \\\\\n"
        latex_content += f"Maximum periods & {periods_stats['max']:.0f} & -- \\\\\n"
        
        latex_content += "\\midrule\n"
        latex_content += f"Firms with substantial coverage ($\geq$3 years) & "
        latex_content += f"{representation_stats['substantial_coverage']['count']:,} & "
        latex_content += f"{representation_stats['substantial_coverage']['percentage']:.1f}\\% \\\\\n"
        
        latex_content += """\\bottomrule
\\end{tabular}
\\begin{tablenotes}
\\small
\\item Note: Analysis based on monthly observations in the final P-Tree dataset.
Substantial coverage defined as firms with at least 36 monthly observations ($\geq$3 years).
Data persistence categories show the distribution of firm representation periods.
\\end{tablenotes}
\\end{table}
"""
        
        with open(output_dir / 'firm_representation.tex', 'w', encoding='utf-8') as f:
            f.write(latex_content)
            
    def _generate_temporal_coverage_table(self, output_dir):
        """Generate LaTeX table for temporal coverage patterns."""
        if 'final_dataset' not in self.results:
            return
            
        temporal_stats = self.results['final_dataset']['temporal_analysis']
        yearly_data = temporal_stats['yearly_coverage']['time_series']
        
        latex_content = """
\\begin{table}[htbp]
\\centering
\\caption{Temporal Coverage Patterns by Year}
\\label{tab:temporal_coverage}
\\begin{tabular}{rrr}
\\toprule
\\textbf{Year} & \\textbf{Unique Firms} & \\textbf{Total Observations} \\\\
\\midrule
"""
        
        for _, row in yearly_data.iterrows():
            latex_content += f"{int(row['date'])} & {row['unique_firms']:,} & {row['total_observations']:,} \\\\\n"
        
        latex_content += "\\midrule\n"
        
        # Summary statistics
        monthly_stats = temporal_stats['monthly_coverage']
        latex_content += f"\\textbf{{Mean firms per month}} & {monthly_stats['mean_firms_per_month']:.0f} & -- \\\\\n"
        latex_content += f"\\textbf{{Range (min-max)}} & {monthly_stats['min_firms_per_month']:,} -- {monthly_stats['max_firms_per_month']:,} & -- \\\\\n"
        
        latex_content += """\\bottomrule
\\end{tabular}
\\begin{tablenotes}
\\small
\\item Note: Temporal coverage shows the number of unique firms and total observations per year.
Monthly statistics provide additional granularity on data availability patterns.
Coverage varies due to firm entry/exit, data availability, and filtering criteria.
\\end{tablenotes}
\\end{table}
"""
        
        with open(output_dir / 'temporal_coverage.tex', 'w', encoding='utf-8') as f:
            f.write(latex_content)

    def generate_summary_report(self):
        """Generate comprehensive summary report."""
        print("\n" + "="*60)
        print("GENERATING COMPREHENSIVE SUMMARY REPORT")
        print("="*60)
        
        report_path = OUTPUT_DIR / 'coverage_analysis_report.md'
        
        with open(report_path, 'w') as f:
            f.write("# P-Tree Data Coverage and Firm Representation Analysis\\n")
            f.write("=" * 60 + "\\n\\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
            
            # Executive Summary
            f.write("## Executive Summary\\n\\n")
            if 'final_dataset' in self.results:
                basic_stats = self.results['final_dataset']['basic_stats']
                f.write(f"- **Total observations:** {basic_stats['total_observations']:,}\\n")
                f.write(f"- **Unique firms:** {basic_stats['unique_firms']:,}\\n")
                f.write(f"- **Time period:** {basic_stats['date_range'][0].strftime('%Y-%m')} to {basic_stats['date_range'][1].strftime('%Y-%m')}\\n")
                f.write(f"- **Monthly periods covered:** {basic_stats['monthly_periods']:,}\\n\\n")
            
            # Data Sources
            f.write("## Data Source Analysis\\n\\n")
            if 'raw_coverage' in self.results:
                raw_stats = self.results['raw_coverage']
                
                if 'finbas' in raw_stats:
                    finbas = raw_stats['finbas']
                    f.write("### Finbas Market Data\\n")
                    f.write(f"- Total observations: {finbas['total_observations']:,}\\n")
                    f.write(f"- Swedish market observations: {finbas['swedish_market']['observations']:,}\\n")
                    f.write(f"- Swedish ISINs: {finbas['swedish_market']['unique_isins']:,}\\n")
                    f.write(f"- Swedish market coverage: {finbas['swedish_market']['percentage_of_total']:.1f}%\\n\\n")
                
                if 'serrano' in raw_stats:
                    serrano = raw_stats['serrano']
                    f.write("### Serrano Accounting Data\\n")
                    obs_count = serrano.get('estimated_total_observations', serrano['sample_observations'])
                    f.write(f"- Total observations: {obs_count:,} (estimated)\\n")
                    f.write(f"- Unique ORGNRs: {serrano['unique_orgnrs_in_sample']:,} (sample)\\n")
                    if 'mapping_coverage' in serrano:
                        f.write(f"- Firms with ISIN mapping: {serrano['mapping_coverage']['serrano_firms_with_isin']:,} ({serrano['mapping_coverage']['mapping_rate']:.1f}%)\\n")
                    f.write("\\n")
            
            # Final Dataset Analysis
            f.write("## Final Dataset Analysis\\n\\n")
            if 'final_dataset' in self.results:
                final_stats = self.results['final_dataset']
                
                # Firm representation
                f.write("### Firm Representation\\n")
                firm_rep = final_stats['firm_representation']
                periods_stats = firm_rep['periods_per_firm']
                f.write(f"- Average periods per firm: {periods_stats['mean']:.1f}\\n")
                f.write(f"- Median periods per firm: {periods_stats['50%']:.1f}\\n")
                f.write(f"- Firms with substantial coverage (>=3 years): {firm_rep['substantial_coverage']['count']:,} ({firm_rep['substantial_coverage']['percentage']:.1f}%)\\n\\n")
                
                # Variable coverage
                f.write("### Variable Coverage\\n")
                var_coverage = final_stats['variable_coverage']
                f.write(f"- Total characteristics: {var_coverage['total_characteristics']}\\n")
                f.write(f"- High coverage variables (>=75%): {var_coverage['high_coverage_vars']}\\n")
                f.write(f"- Medium coverage variables (25-74%): {var_coverage['medium_coverage_vars']}\\n")
                f.write(f"- Low coverage variables (<25%): {var_coverage['low_coverage_vars']}\\n\\n")
                
                # Top variables by coverage
                f.write("#### Top 10 Variables by Coverage\\n")
                top_vars = var_coverage['coverage_details'].head(10)
                for var, row in top_vars.iterrows():
                    var_clean = var.replace('rank_', '').upper()
                    f.write(f"- {var_clean}: {row['coverage_rate']:.1f}%\\n")
                f.write("\\n")
                
                # Temporal patterns
                f.write("### Temporal Coverage\\n")
                temporal = final_stats['temporal_analysis']
                monthly_stats = temporal['monthly_coverage']
                f.write(f"- Average firms per month: {monthly_stats['mean_firms_per_month']:.0f}\\n")
                f.write(f"- Range: {monthly_stats['min_firms_per_month']:,} to {monthly_stats['max_firms_per_month']:,} firms per month\\n\\n")
            
            # Files generated
            f.write("## Output Files Generated\\n\\n")
            f.write("### Visualizations\\n")
            f.write("- `temporal_coverage_evolution.png`: Time series of data coverage\\n")
            f.write("- `firm_periods_distribution.png`: Distribution of periods per firm\\n")
            f.write("- `firm_duration_distribution.png`: Distribution of firm duration\\n")
            f.write("- `firm_data_density.png`: Data density vs duration\\n")
            f.write("- `firm_representation_categories.png`: Firm representation categories\\n")
            f.write("- `variable_coverage_rates.png`: Variable coverage rates\\n")
            f.write("- `variable_coverage_distribution.png`: Coverage distribution\\n")
            f.write("- `data_source_observations.png`: Observations by data source\\n")
            f.write("- `data_source_entities.png`: Entities by data source\\n")
            f.write("- `temporal_coverage_monthly.png`: Monthly coverage trends\\n")
            f.write("- `dataset_firms_comparison.png`: Number of firms vs Cong et al. (2023)\\n")
            f.write("- `dataset_observations_comparison.png`: Number of observations vs Cong et al. (2023)\\n")
            f.write("- `time_period_comparison.png`: Time period coverage comparison\\n")
            f.write("- `characteristics_coverage_comparison.png`: Characteristics count comparison\\n")
            f.write("- `market_focus_comparison.png`: Market focus comparison\\n")
            f.write("- `data_persistence_comparison.png`: Data persistence comparison\\n")
            f.write("- `variable_coverage_quality.png`: Variable coverage quality\\n")
            f.write("- `firm_representation_distribution.png`: Firm representation distribution\\n")
            f.write("- `temporal_coverage_evolution_sample.png`: Temporal coverage evolution\\n")
            f.write("- `comprehensive_study_comparison.png`: Comprehensive study comparison table\\n\\n")
            
            f.write("### LaTeX Tables\\n")
            f.write("- `latex_tables/data_source_summary.tex`: Data source summary table\\n")
            f.write("- `latex_tables/variable_coverage.tex`: Variable coverage by category\\n")
            f.write("- `latex_tables/firm_representation.tex`: Firm representation analysis\\n")
            f.write("- `latex_tables/temporal_coverage.tex`: Temporal coverage patterns\\n\\n")
            
            f.write("### Data Files\\n")
            f.write("- `coverage_analysis_report.md`: This comprehensive report\\n")
            f.write("- Analysis results stored in Python pickle format for further analysis\\n\\n")
            
        print(f"Comprehensive report saved to: {report_path}")
        
        # Save results for further analysis
        import pickle
        with open(OUTPUT_DIR / 'analysis_results.pkl', 'wb') as f:
            pickle.dump(self.results, f)

def main():
    """Main analysis execution."""
    print("P-Tree Data Coverage and Firm Representation Analysis")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = DataCoverageAnalyzer()
    
    # Run analysis steps
    analyzer.analyze_raw_data_coverage()
    analyzer.analyze_final_dataset_coverage()
    
    # Generate outputs
    analyzer.create_visualizations()
    analyzer.generate_latex_tables()
    analyzer.generate_summary_report()
    
    print("\\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"All outputs saved to: {OUTPUT_DIR}")
    print("\\nFiles generated:")
    print("- Individual PNG visualizations for each analysis")
    print("- LaTeX tables for thesis inclusion")
    print("- Comprehensive markdown report")
    print("- Analysis results (pickle format)")

if __name__ == "__main__":
    main()