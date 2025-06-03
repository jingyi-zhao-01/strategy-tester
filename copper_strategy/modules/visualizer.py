"""
Visualization module for the trading strategy.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import logging

logger = logging.getLogger(__name__)

class StrategyVisualizer:
    """
    Visualizes the trading strategy results.
    """
    
    def __init__(self, config):
        """
        Initialize the visualizer.
        
        Args:
            config (module): Configuration settings
        """
        self.config = config
    
    def plot_strategy_results(self, df, position1_results, position2_results, output_path=None):
        """
        Plot the strategy results.
        
        Args:
            df (pandas.DataFrame): Market data with indicators
            position1_results (pandas.DataFrame): Position 1 results
            position2_results (pandas.DataFrame): Position 2 results
            output_path (str): Path to save the plot
            
        Returns:
            matplotlib.figure.Figure: The figure object
        """
        # For hourly data, we'll only plot the last N days to make the chart more readable
        plot_days = self.config.PLOT_DAYS
        hours_to_plot = plot_days * 24
        plot_start_idx = max(0, len(df) - hours_to_plot)
        plot_df = df.iloc[plot_start_idx:]
        
        # Create figure
        plt.figure(figsize=self.config.CHART_SIZE)
        
        # Price chart
        plt.subplot(4, 1, 1)
        plt.plot(plot_df.index, plot_df['Close'], label=f'Copper Futures Price (Last {plot_days} Days)')
        
        # Plot entry points
        entry_dates = []
        entry_prices = []
        
        # Extract entry points from position results
        for _, row in position1_results.iterrows():
            entry_dates.append(row['Entry Date'])
            entry_prices.append(row['Entry Price'])
        
        # Plot entry points
        for i, (date, price) in enumerate(zip(entry_dates, entry_prices)):
            if date in plot_df.index:
                plt.scatter(date, price, color='green', marker='^', s=100)
        
        # Plot exit points for position 1
        for _, row in position1_results.iterrows():
            if row['Exit Date'] in plot_df.index:
                if row['Exit Reason'] == 'Take Profit':
                    plt.scatter(row['Exit Date'], row['Exit Price'], color='blue', marker='o', s=100)
                elif row['Exit Reason'] == 'Stop Loss':
                    plt.scatter(row['Exit Date'], row['Exit Price'], color='purple', marker='v', s=100)
        
        # Plot exit points for position 2
        for _, row in position2_results.iterrows():
            if row['Exit Date'] in plot_df.index:
                if row['Exit Reason'] == 'Trend Reversal':
                    plt.scatter(row['Exit Date'], row['Exit Price'], color='orange', marker='x', s=100)
                elif row['Exit Reason'] == 'Stop Loss':
                    plt.scatter(row['Exit Date'], row['Exit Price'], color='purple', marker='v', s=100)
        
        plt.title(f"Copper Futures 1-Hour Price (Last {plot_days} Days) with Entry/Exit Points\n"
                 f"(Green=Entry, Triangle=Pos1, X=Pos2, Purple=Stop Loss, Blue=Take Profit, Orange=Trend Reversal)")
        plt.legend()
        
        # Primary MACD
        plt.subplot(4, 1, 2)
        plt.plot(plot_df.index, plot_df['macd_p'], 
                 label=f'MACD Primary ({self.config.PRIMARY_MACD_FAST},{self.config.PRIMARY_MACD_SLOW},{self.config.PRIMARY_MACD_SIGNAL})')
        plt.plot(plot_df.index, plot_df['signal_p'], label='Signal Primary')
        plt.bar(plot_df.index, plot_df['macd_diff_p'], color='gray', alpha=0.3, label='MACD Histogram')
        
        # Highlight bullish and bearish trend reversal points
        bullish_reversal_dates = plot_df[plot_df['bullish_reversal'] == True].index
        bearish_reversal_dates = plot_df[plot_df['bearish_reversal'] == True].index
        
        for date in bullish_reversal_dates:
            plt.axvline(x=date, color='green', linestyle='--', alpha=0.5)
            
        for date in bearish_reversal_dates:
            plt.axvline(x=date, color='red', linestyle='--', alpha=0.5)
            
        plt.title(f"Primary MACD ({self.config.PRIMARY_MACD_FAST},{self.config.PRIMARY_MACD_SLOW},{self.config.PRIMARY_MACD_SIGNAL}) "
                 f"with Bullish/Bearish Trend Reversals (Last {plot_days} Days)")
        plt.legend()
        
        # Secondary MACD
        plt.subplot(4, 1, 3)
        plt.plot(plot_df.index, plot_df['macd_f'], 
                 label=f'MACD Fast ({self.config.SECONDARY_MACD_FAST},{self.config.SECONDARY_MACD_SLOW},{self.config.SECONDARY_MACD_SIGNAL})')
        plt.plot(plot_df.index, plot_df['signal_f'], label='Signal Fast')
        plt.bar(plot_df.index, plot_df['macd_diff_f'], color='gray', alpha=0.3, label='MACD Histogram')
        
        # Highlight crossover points
        cross_up_dates = plot_df[plot_df['f_cross_up'] == True].index
        cross_down_dates = plot_df[plot_df['f_cross_down'] == True].index
        
        for date in cross_up_dates:
            plt.axvline(x=date, color='green', linestyle='--', alpha=0.5)
            
        for date in cross_down_dates:
            plt.axvline(x=date, color='red', linestyle='--', alpha=0.5)
            
        plt.title(f"Secondary MACD ({self.config.SECONDARY_MACD_FAST},{self.config.SECONDARY_MACD_SLOW},{self.config.SECONDARY_MACD_SIGNAL}) "
                 f"with Crossovers (Last {plot_days} Days)")
        plt.legend()
        
        # Slope and Parallel Lines
        plt.subplot(4, 1, 4)
        plt.plot(plot_df.index, plot_df['macd_p_slope_short'], label='Short-term MACD Slope')
        plt.plot(plot_df.index, plot_df['macd_p_slope_long'], label='Long-term MACD Slope')
        plt.plot(plot_df.index, plot_df['signal_p_slope_long'], label='Long-term Signal Slope')
        plt.bar(plot_df.index, plot_df['parallel_lines'].astype(int) * 0.01, color='blue', alpha=0.3, label='Parallel Lines')
        plt.bar(plot_df.index, plot_df['fast_line_snap'].astype(int) * 0.02, color='red', alpha=0.3, label='Fast Line Snap')
        plt.bar(plot_df.index, plot_df['bullish_reversal'].astype(int) * 0.03, color='green', alpha=0.5, label='Bullish Reversal')
        plt.bar(plot_df.index, plot_df['bearish_reversal'].astype(int) * -0.03, color='purple', alpha=0.5, label='Bearish Reversal')
        
        plt.title(f"MACD Slopes and Trend Reversal Detection (Last {plot_days} Days)")
        plt.legend()
        
        plt.tight_layout()
        
        # Save the figure if output path is provided
        if output_path:
            plt.savefig(output_path)
            logger.info(f"Chart saved to {output_path}")
        
        return plt.gcf()
    
    def print_performance_summary(self, combined_results, position1_metrics, position2_metrics):
        """
        Print a summary of the strategy performance.
        
        Args:
            combined_results (dict): Combined performance metrics
            position1_metrics (dict): Position 1 performance metrics
            position2_metrics (dict): Position 2 performance metrics
        """
        print(f"Total Trades: {combined_results['total_trades']} | "
              f"Combined Return: {combined_results['total_return']*100:.2f}% | "
              f"Win Rate: {combined_results['win_rate']*100:.2f}% | "
              f"Avg Return: {combined_results['avg_return']*100:.2f}%")
        
        print("\nPosition 1 (Take Profit at {}x Risk):".format(self.config.RISK_REWARD_RATIO))
        print(f"Trades: {position1_metrics['trades']} | "
              f"Total Return: {position1_metrics['total_return']*100:.2f}% | "
              f"Win Rate: {position1_metrics['win_rate']*100:.2f}% | "
              f"Avg Return: {position1_metrics['avg_return']*100:.2f}%")
        print(f"Exit Reasons: {position1_metrics['exit_reasons']}")
        
        print("\nPosition 2 (Exit on Trend Reversal):")
        print(f"Trades: {position2_metrics['trades']} | "
              f"Total Return: {position2_metrics['total_return']*100:.2f}% | "
              f"Win Rate: {position2_metrics['win_rate']*100:.2f}% | "
              f"Avg Return: {position2_metrics['avg_return']*100:.2f}%")
        print(f"Exit Reasons: {position2_metrics['exit_reasons']}")
        
        # Print performance by exit reason
        print("\nPosition 1 Performance by Exit Reason:")
        for reason, metrics in position1_metrics['by_reason'].items():
            print(f"{reason}: {metrics['trades']} trades | "
                  f"Win Rate: {metrics['win_rate']*100:.2f}% | "
                  f"Avg Return: {metrics['avg_return']*100:.2f}%")
        
        print("\nPosition 2 Performance by Exit Reason:")
        for reason, metrics in position2_metrics['by_reason'].items():
            print(f"{reason}: {metrics['trades']} trades | "
                  f"Win Rate: {metrics['win_rate']*100:.2f}% | "
                  f"Avg Return: {metrics['avg_return']*100:.2f}%")