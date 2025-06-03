"""
Core strategy logic for generating entry and exit signals.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TrendReversalStrategy:
    """
    Dual MACD trend reversal strategy with two position management approaches.
    """
    
    def __init__(self, config):
        """
        Initialize the strategy.
        
        Args:
            config (module): Configuration settings
        """
        self.config = config
    
    def generate_signals(self, df):
        """
        Generate entry and exit signals.
        
        Args:
            df (pandas.DataFrame): Market data with indicators
            
        Returns:
            pandas.DataFrame: DataFrame with entry and exit signals
        """
        # Entry signal: Secondary MACD crosses above signal while primary MACD is bullish
        df['trend_up'] = df['macd_p'] > df['signal_p']
        df['entry'] = (df['macd_f'] > df['signal_f']) & (df['macd_f'].shift(1) <= df['signal_f'].shift(1)) & df['trend_up']
        
        # Exit signal for position 2: Secondary MACD crosses below signal while primary MACD is bullish
        df['exit'] = (df['macd_f'] < df['signal_f']) & (df['macd_f'].shift(1) >= df['signal_f'].shift(1)) & df['trend_up']
        
        # Exit signal for position 1 will be determined by the position manager (take profit or stop loss)
        
        # Additional exit signal for position 2: Primary MACD trend reversal
        df['trend_reversal_exit'] = df['bearish_reversal']
        
        logger.info(f"Generated {df['entry'].sum()} entry signals and {df['exit'].sum()} exit signals")
        
        return df
    
    def filter_signals(self, df):
        """
        Apply additional filters to entry and exit signals.
        
        Args:
            df (pandas.DataFrame): Market data with signals
            
        Returns:
            pandas.DataFrame: DataFrame with filtered signals
        """
        # Filter out entry signals that occur too close to each other
        min_bars_between_entries = 4  # Minimum number of bars between entries
        
        entry_indices = df.index[df['entry']].tolist()
        filtered_entries = []
        
        if entry_indices:
            filtered_entries.append(entry_indices[0])
            
            for i in range(1, len(entry_indices)):
                current_idx = df.index.get_loc(entry_indices[i])
                prev_idx = df.index.get_loc(filtered_entries[-1])
                
                if current_idx - prev_idx >= min_bars_between_entries:
                    filtered_entries.append(entry_indices[i])
        
        # Create a new column for filtered entries
        df['filtered_entry'] = False
        df.loc[filtered_entries, 'filtered_entry'] = True
        
        logger.info(f"Filtered to {df['filtered_entry'].sum()} entry signals")
        
        return df