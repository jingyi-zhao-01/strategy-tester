"""
Data loading and preprocessing module for the trading strategy.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_market_data(symbol, interval="1h", lookback_days=60):
    """
    Load market data from Yahoo Finance.
    
    Args:
        symbol (str): The ticker symbol to download
        interval (str): Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        lookback_days (int): Number of days to look back
        
    Returns:
        pandas.DataFrame: DataFrame with market data
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    logger.info(f"Downloading {interval} data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    df = yf.download(symbol, start=start_date, end=end_date, interval=interval)
    
    if df.empty:
        logger.error(f"No data found for {symbol} with interval {interval}")
        raise ValueError(f"No data found for {symbol} with interval {interval}")
    
    # Handle multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        # Create a new DataFrame with flattened column names
        new_df = pd.DataFrame(index=df.index)
        for col_type in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if (col_type, symbol) in df.columns:
                new_df[col_type] = df[(col_type, symbol)]
        df = new_df
    
    # Clean the data
    df = df.dropna()
    
    logger.info(f"Loaded {len(df)} {interval} bars from {df.index[0]} to {df.index[-1]}")
    
    return df

def preprocess_data(df):
    """
    Preprocess the market data.
    
    Args:
        df (pandas.DataFrame): Raw market data
        
    Returns:
        pandas.DataFrame: Preprocessed market data
    """
    # Make a copy to avoid modifying the original
    processed_df = df.copy()
    
    # Ensure the index is datetime
    if not isinstance(processed_df.index, pd.DatetimeIndex):
        processed_df.index = pd.to_datetime(processed_df.index)
    
    # Sort by date
    processed_df = processed_df.sort_index()
    
    # Add basic price features
    processed_df['PriceChange'] = processed_df['Close'] - processed_df['Open']
    processed_df['PriceChangePercent'] = (processed_df['Close'] / processed_df['Open'] - 1) * 100
    
    # Add day of week and hour of day for potential time-based patterns
    processed_df['DayOfWeek'] = processed_df.index.dayofweek
    processed_df['HourOfDay'] = processed_df.index.hour
    
    return processed_df