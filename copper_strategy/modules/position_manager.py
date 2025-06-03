"""
Position management for the trading strategy.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class PositionManager:
    """
    Manages trading positions, including entries, exits, stop losses, and take profits.
    """
    
    def __init__(self, config):
        """
        Initialize the position manager.
        
        Args:
            config (module): Configuration settings
        """
        self.config = config
    
    def calculate_stop_loss(self, df, current_idx, entry_price):
        """
        Calculate stop loss price based on recent lows or a percentage.
        
        Args:
            df (pandas.DataFrame): Market data
            current_idx (int): Current index in the dataframe
            entry_price (float): Entry price
            
        Returns:
            float: Stop loss price
        """
        # Look back for the lowest price in the lookback period
        lookback_period = min(self.config.STOP_LOSS_LOOKBACK, current_idx)
        
        # Extract recent prices
        recent_prices = []
        for j in range(current_idx - lookback_period, current_idx + 1):
            recent_prices.append(float(df['Close'].iloc[j]))
        
        recent_low = min(recent_prices)
        
        # Set stop loss to either recent low minus a buffer or a percentage of current price
        buffer_pct = self.config.STOP_LOSS_BUFFER
        percentage_stop = entry_price * (1 - self.config.DEFAULT_STOP_LOSS_PCT)
        
        # Use the higher of the two (less aggressive stop loss)
        stop_loss_price = max(recent_low * (1 - buffer_pct), percentage_stop)
        
        return stop_loss_price
    
    def calculate_take_profit(self, entry_price, stop_loss_price):
        """
        Calculate take profit price based on risk-reward ratio.
        
        Args:
            entry_price (float): Entry price
            stop_loss_price (float): Stop loss price
            
        Returns:
            float: Take profit price
        """
        risk = entry_price - stop_loss_price
        take_profit_price = entry_price + (risk * self.config.RISK_REWARD_RATIO)
        
        return take_profit_price
    
    def backtest_positions(self, df):
        """
        Backtest the dual position strategy.
        
        Args:
            df (pandas.DataFrame): Market data with signals
            
        Returns:
            tuple: (position1_results, position2_results, combined_results)
        """
        # Initialize position tracking
        position1_active = False
        position2_active = False
        
        # Track entry and exit points
        entry_dates = []
        entry_prices = []
        
        # Position 1 (Take Profit) tracking
        position1_exit_dates = []
        position1_exit_prices = []
        position1_returns = []
        position1_exit_reasons = []
        
        # Position 2 (Trend Reversal) tracking
        position2_exit_dates = []
        position2_exit_prices = []
        position2_returns = []
        position2_exit_reasons = []
        
        # Stop loss and take profit levels
        stop_loss_price = 0
        take_profit_price_1 = 0
        
        # Backtest loop
        for i in range(len(df)):
            current_price = float(df['Close'].iloc[i])
            
            # Check for entry signal
            if df['filtered_entry'].iloc[i] and not position1_active and not position2_active:
                # Enter both positions
                position1_active = True
                position2_active = True
                
                entry_price = current_price
                entry_dates.append(df.index[i])
                entry_prices.append(entry_price)
                
                # Calculate stop loss and take profit levels
                stop_loss_price = self.calculate_stop_loss(df, i, entry_price)
                take_profit_price_1 = self.calculate_take_profit(entry_price, stop_loss_price)
            
            # Check for position 1 exit (take profit or stop loss)
            if position1_active:
                # Check for take profit
                if current_price >= take_profit_price_1:
                    position1_active = False
                    position1_exit_dates.append(df.index[i])
                    position1_exit_prices.append(current_price)
                    position1_returns.append((current_price - entry_prices[-1]) / entry_prices[-1])
                    position1_exit_reasons.append("Take Profit")
                
                # Check for stop loss
                elif current_price <= stop_loss_price:
                    position1_active = False
                    position1_exit_dates.append(df.index[i])
                    position1_exit_prices.append(current_price)
                    position1_returns.append((current_price - entry_prices[-1]) / entry_prices[-1])
                    position1_exit_reasons.append("Stop Loss")
            
            # Check for position 2 exit (trend reversal or stop loss)
            if position2_active:
                # Check for trend reversal exit
                if df['exit'].iloc[i] or df['trend_reversal_exit'].iloc[i]:
                    position2_active = False
                    position2_exit_dates.append(df.index[i])
                    position2_exit_prices.append(current_price)
                    position2_returns.append((current_price - entry_prices[-1]) / entry_prices[-1])
                    position2_exit_reasons.append("Trend Reversal")
                
                # Check for stop loss
                elif current_price <= stop_loss_price:
                    position2_active = False
                    position2_exit_dates.append(df.index[i])
                    position2_exit_prices.append(current_price)
                    position2_returns.append((current_price - entry_prices[-1]) / entry_prices[-1])
                    position2_exit_reasons.append("Stop Loss")
        
        # Create results dataframes
        position1_results = pd.DataFrame({
            'Entry Date': entry_dates[:len(position1_exit_dates)],
            'Entry Price': entry_prices[:len(position1_exit_dates)],
            'Exit Date': position1_exit_dates,
            'Exit Price': position1_exit_prices,
            'Return': [f"{r*100:.2f}%" for r in position1_returns],
            'Return_float': position1_returns,
            'Exit Reason': position1_exit_reasons
        })
        
        position2_results = pd.DataFrame({
            'Entry Date': entry_dates[:len(position2_exit_dates)],
            'Entry Price': entry_prices[:len(position2_exit_dates)],
            'Exit Date': position2_exit_dates,
            'Exit Price': position2_exit_prices,
            'Return': [f"{r*100:.2f}%" for r in position2_returns],
            'Return_float': position2_returns,
            'Exit Reason': position2_exit_reasons
        })
        
        # Calculate combined results
        combined_returns = position1_returns + position2_returns
        combined_results = {
            'total_trades': len(position1_returns) + len(position2_returns),
            'total_return': sum(position1_returns) + sum(position2_returns),
            'win_rate': (sum(1 for r in combined_returns if r > 0) / len(combined_returns)) if combined_returns else 0,
            'avg_return': sum(combined_returns) / len(combined_returns) if combined_returns else 0
        }
        
        # Calculate position-specific metrics
        position1_metrics = {
            'trades': len(position1_returns),
            'total_return': sum(position1_returns),
            'win_rate': (sum(1 for r in position1_returns if r > 0) / len(position1_returns)) if position1_returns else 0,
            'avg_return': sum(position1_returns) / len(position1_returns) if position1_returns else 0,
            'exit_reasons': {reason: position1_exit_reasons.count(reason) for reason in set(position1_exit_reasons)}
        }
        
        position2_metrics = {
            'trades': len(position2_returns),
            'total_return': sum(position2_returns),
            'win_rate': (sum(1 for r in position2_returns if r > 0) / len(position2_returns)) if position2_returns else 0,
            'avg_return': sum(position2_returns) / len(position2_returns) if position2_returns else 0,
            'exit_reasons': {reason: position2_exit_reasons.count(reason) for reason in set(position2_exit_reasons)}
        }
        
        # Add exit reason performance
        position1_by_reason = {}
        position2_by_reason = {}
        
        for reason in set(position1_exit_reasons):
            reason_returns = [position1_returns[i] for i in range(len(position1_returns)) if position1_exit_reasons[i] == reason]
            position1_by_reason[reason] = {
                'trades': len(reason_returns),
                'win_rate': sum(1 for r in reason_returns if r > 0) / len(reason_returns) if reason_returns else 0,
                'avg_return': sum(reason_returns) / len(reason_returns) if reason_returns else 0
            }
        
        for reason in set(position2_exit_reasons):
            reason_returns = [position2_returns[i] for i in range(len(position2_returns)) if position2_exit_reasons[i] == reason]
            position2_by_reason[reason] = {
                'trades': len(reason_returns),
                'win_rate': sum(1 for r in reason_returns if r > 0) / len(reason_returns) if reason_returns else 0,
                'avg_return': sum(reason_returns) / len(reason_returns) if reason_returns else 0
            }
        
        # Add to metrics
        position1_metrics['by_reason'] = position1_by_reason
        position2_metrics['by_reason'] = position2_by_reason
        
        return position1_results, position2_results, combined_results, position1_metrics, position2_metrics