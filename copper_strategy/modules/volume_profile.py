"""
Volume Profile Analysis Module.

This module provides functionality to analyze volume profiles and identify
key price levels based on volume distribution.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import logging

logger = logging.getLogger(__name__)

class VolumeProfileAnalyzer:
    """
    Analyzes volume profiles to identify key price levels.
    """
    
    def __init__(self, price_precision=0.01, min_prominence=0.1):
        """
        Initialize the volume profile analyzer.
        
        Args:
            price_precision (float): Price precision for binning
            min_prominence (float): Minimum prominence for peak detection
        """
        self.price_precision = price_precision
        self.min_prominence = min_prominence
    
    def calculate_volume_profile(self, df, lookback_periods=None):
        """
        Calculate volume profile for a given dataframe.
        
        Args:
            df (pandas.DataFrame): Market data with price and volume
            lookback_periods (int): Number of periods to look back, None for all data
            
        Returns:
            pandas.DataFrame: Volume profile data
        """
        # Use only the specified lookback period if provided
        if lookback_periods is not None:
            df = df.iloc[-lookback_periods:]
        
        # Create price bins
        price_min = df['Low'].min()
        price_max = df['High'].max()
        
        # Calculate number of bins based on price range and precision
        num_bins = int((price_max - price_min) / self.price_precision) + 1
        
        # Create price bins
        price_bins = np.linspace(price_min, price_max, num_bins)
        
        # Initialize volume profile
        volume_profile = pd.DataFrame({
            'price': price_bins,
            'volume': 0.0
        })
        
        # Distribute volume across price bins
        for _, row in df.iterrows():
            # Find bins that fall within the candle's range
            mask = (volume_profile['price'] >= row['Low']) & (volume_profile['price'] <= row['High'])
            
            # Distribute volume equally across all bins in the candle's range
            if mask.sum() > 0:
                volume_per_bin = row['Volume'] / mask.sum()
                volume_profile.loc[mask, 'volume'] += volume_per_bin
        
        # Calculate cumulative volume
        volume_profile['cumulative_volume'] = volume_profile['volume'].cumsum()
        volume_profile['volume_percentage'] = volume_profile['volume'] / volume_profile['volume'].sum() * 100
        
        return volume_profile
    
    def identify_key_levels(self, volume_profile):
        """
        Identify key price levels from volume profile.
        
        Args:
            volume_profile (pandas.DataFrame): Volume profile data
            
        Returns:
            dict: Key price levels
        """
        # Find peaks in volume distribution
        peaks, properties = find_peaks(
            volume_profile['volume'].values,
            prominence=self.min_prominence * volume_profile['volume'].max()
        )
        
        # Extract peak prices and volumes
        peak_prices = volume_profile['price'].iloc[peaks].values
        peak_volumes = volume_profile['volume'].iloc[peaks].values
        
        # Sort peaks by volume
        sorted_indices = np.argsort(peak_volumes)[::-1]  # Descending order
        sorted_peak_prices = peak_prices[sorted_indices]
        sorted_peak_volumes = peak_volumes[sorted_indices]
        
        # Calculate value area (70% of volume)
        total_volume = volume_profile['volume'].sum()
        value_area_threshold = 0.7 * total_volume
        
        cumulative_vol = 0
        value_area_indices = []
        
        for i, vol in enumerate(sorted_peak_volumes):
            cumulative_vol += vol
            value_area_indices.append(sorted_indices[i])
            if cumulative_vol >= value_area_threshold:
                break
        
        # Get value area high and low
        if value_area_indices:
            value_area_prices = peak_prices[value_area_indices]
            value_area_high = np.max(value_area_prices)
            value_area_low = np.min(value_area_prices)
        else:
            value_area_high = volume_profile['price'].max()
            value_area_low = volume_profile['price'].min()
        
        # Calculate point of control (price with highest volume)
        point_of_control = volume_profile.loc[volume_profile['volume'].idxmax(), 'price']
        
        # Calculate volume-weighted average price (VWAP)
        vwap = np.sum(volume_profile['price'] * volume_profile['volume']) / volume_profile['volume'].sum()
        
        # Return key levels
        return {
            'point_of_control': point_of_control,
            'value_area_high': value_area_high,
            'value_area_low': value_area_low,
            'vwap': vwap,
            'high_volume_nodes': sorted_peak_prices[:3].tolist() if len(sorted_peak_prices) >= 3 else sorted_peak_prices.tolist(),
            'all_peaks': list(zip(peak_prices, peak_volumes))
        }
    
    def plot_volume_profile(self, volume_profile, key_levels, ax=None):
        """
        Plot volume profile with key levels.
        
        Args:
            volume_profile (pandas.DataFrame): Volume profile data
            key_levels (dict): Key price levels
            ax (matplotlib.axes.Axes): Matplotlib axes to plot on
            
        Returns:
            matplotlib.axes.Axes: The axes object
        """
        if ax is None:
            _, ax = plt.subplots(figsize=(10, 6))
        
        # Plot horizontal volume bars
        ax.barh(volume_profile['price'], volume_profile['volume'], height=self.price_precision, alpha=0.6)
        
        # Plot key levels
        ax.axhline(y=key_levels['point_of_control'], color='r', linestyle='-', linewidth=2, label='Point of Control')
        ax.axhline(y=key_levels['value_area_high'], color='g', linestyle='--', linewidth=1, label='Value Area High')
        ax.axhline(y=key_levels['value_area_low'], color='g', linestyle='--', linewidth=1, label='Value Area Low')
        ax.axhline(y=key_levels['vwap'], color='b', linestyle=':', linewidth=1, label='VWAP')
        
        # Plot high volume nodes
        for i, price in enumerate(key_levels['high_volume_nodes']):
            if i == 0:
                ax.axhline(y=price, color='purple', linestyle='-', linewidth=1, alpha=0.5, label='High Volume Node')
            else:
                ax.axhline(y=price, color='purple', linestyle='-', linewidth=1, alpha=0.5)
        
        ax.set_ylabel('Price')
        ax.set_xlabel('Volume')
        ax.set_title('Volume Profile')
        ax.legend()
        
        return ax
    
    def analyze(self, df, lookback_periods=None):
        """
        Analyze volume profile and identify key levels.
        
        Args:
            df (pandas.DataFrame): Market data with price and volume
            lookback_periods (int): Number of periods to look back, None for all data
            
        Returns:
            tuple: (volume_profile, key_levels)
        """
        volume_profile = self.calculate_volume_profile(df, lookback_periods)
        key_levels = self.identify_key_levels(volume_profile)
        
        return volume_profile, key_levels