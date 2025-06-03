"""
Technical indicators for the trading strategy.
"""

import pandas as pd
import numpy as np
from ta.trend import MACD
import logging

logger = logging.getLogger(__name__)

def calculate_macd(df, column='Close', window_fast=12, window_slow=26, window_sign=9, prefix=''):
    """
    Calculate MACD indicator.
    
    Args:
        df (pandas.DataFrame): Market data
        column (str): Column to use for calculation
        window_fast (int): Fast EMA window
        window_slow (int): Slow EMA window
        window_sign (int): Signal line window
        prefix (str): Prefix for column names
        
    Returns:
        pandas.DataFrame: DataFrame with MACD indicators added
    """
    macd_indicator = MACD(
        close=df[column], 
        window_slow=window_slow, 
        window_fast=window_fast, 
        window_sign=window_sign
    )
    
    # Add MACD components to the dataframe
    df[f'macd_{prefix}'] = macd_indicator.macd()
    df[f'signal_{prefix}'] = macd_indicator.macd_signal()
    df[f'macd_diff_{prefix}'] = macd_indicator.macd_diff()
    
    # Add crossover signals
    df[f'{prefix}_cross_up'] = (df[f'macd_{prefix}'] > df[f'signal_{prefix}']) & (
        df[f'macd_{prefix}'].shift(1) <= df[f'signal_{prefix}'].shift(1))
    
    df[f'{prefix}_cross_down'] = (df[f'macd_{prefix}'] < df[f'signal_{prefix}']) & (
        df[f'macd_{prefix}'].shift(1) >= df[f'signal_{prefix}'].shift(1))
    
    return df

def calculate_slopes(df, column, short_window=3, long_window=10, prefix=''):
    """
    Calculate short-term and long-term slopes of a column.
    
    Args:
        df (pandas.DataFrame): Market data
        column (str): Column to calculate slopes for
        short_window (int): Short-term window
        long_window (int): Long-term window
        prefix (str): Prefix for column names
        
    Returns:
        pandas.DataFrame: DataFrame with slope indicators added
    """
    # Short-term slope (more responsive)
    df[f'{column}_slope_short'] = df[column].diff(short_window) / short_window
    
    # Long-term slope (smoother)
    df[f'{column}_slope_long'] = df[column].diff(long_window) / long_window
    
    return df

def detect_trend_reversals(df, lookback=20, parallel_threshold=0.0001, snap_threshold=0.0002):
    """
    Detect trend reversals based on MACD line behavior.
    
    Args:
        df (pandas.DataFrame): Market data with MACD indicators
        lookback (int): Lookback period for trend detection
        parallel_threshold (float): Threshold for detecting parallel lines
        snap_threshold (float): Threshold for detecting fast line snap
        
    Returns:
        pandas.DataFrame: DataFrame with trend reversal signals added
    """
    # Detect when MACD and Signal lines are moving in parallel
    slope_diff = abs(df['macd_p_slope_long'] - df['signal_p_slope_long'])
    df['parallel_lines'] = slope_diff < parallel_threshold
    
    # Detect when fast line "snaps" (changes direction quickly)
    df['fast_line_snap'] = abs(df['macd_p_slope_short'] - df['macd_p_slope_short'].shift(1)) > snap_threshold
    
    # Bullish reversal: MACD crosses above signal after being below
    df['bullish_reversal'] = False
    
    # Bearish reversal: MACD crosses below signal after being above
    df['bearish_reversal'] = False
    
    # Detect trend reversals
    for i in range(lookback, len(df)):
        # Check for bullish reversal pattern
        if (df['macd_p'].iloc[i] > df['signal_p'].iloc[i] and 
            df['macd_p'].iloc[i-1] <= df['signal_p'].iloc[i-1]):
            
            # Confirm with slope change
            if (df['macd_p_slope_short'].iloc[i] > 0 and 
                df['macd_p_slope_short'].iloc[i-1] < 0):
                df.loc[df.index[i], 'bullish_reversal'] = True
        
        # Check for bearish reversal pattern
        if (df['macd_p'].iloc[i] < df['signal_p'].iloc[i] and 
            df['macd_p'].iloc[i-1] >= df['signal_p'].iloc[i-1]):
            
            # Confirm with slope change
            if (df['macd_p_slope_short'].iloc[i] < 0 and 
                df['macd_p_slope_short'].iloc[i-1] > 0):
                df.loc[df.index[i], 'bearish_reversal'] = True
    
    return df

def add_all_indicators(df, config):
    """
    Add all technical indicators to the dataframe.
    
    Args:
        df (pandas.DataFrame): Market data
        config (module): Configuration settings
        
    Returns:
        pandas.DataFrame: DataFrame with all indicators added
    """
    # Calculate primary MACD (for trend detection)
    df = calculate_macd(
        df, 
        window_fast=config.PRIMARY_MACD_FAST,
        window_slow=config.PRIMARY_MACD_SLOW, 
        window_sign=config.PRIMARY_MACD_SIGNAL,
        prefix='p'
    )
    
    # Calculate secondary MACD (for entry signals)
    df = calculate_macd(
        df, 
        window_fast=config.SECONDARY_MACD_FAST,
        window_slow=config.SECONDARY_MACD_SLOW, 
        window_sign=config.SECONDARY_MACD_SIGNAL,
        prefix='f'
    )
    
    # Calculate slopes for MACD components
    df = calculate_slopes(
        df, 
        column='macd_p', 
        short_window=config.SHORT_SLOPE_WINDOW, 
        long_window=config.LONG_SLOPE_WINDOW
    )
    
    df = calculate_slopes(
        df, 
        column='signal_p', 
        short_window=config.SHORT_SLOPE_WINDOW, 
        long_window=config.LONG_SLOPE_WINDOW
    )
    
    # Detect trend reversals
    df = detect_trend_reversals(
        df, 
        lookback=config.TREND_REVERSAL_LOOKBACK,
        parallel_threshold=config.PARALLEL_THRESHOLD,
        snap_threshold=config.SNAP_THRESHOLD
    )
    
    return df