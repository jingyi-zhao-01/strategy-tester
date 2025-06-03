"""
Demonstration of Volume Profile integration with the trading strategy.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# Import configuration
from trend_reversal_strategy import config

# Import modules
from trend_reversal_strategy.modules.data_loader import load_market_data, preprocess_data
from trend_reversal_strategy.modules.indicators import add_all_indicators
from trend_reversal_strategy.modules.strategy import TrendReversalStrategy
from trend_reversal_strategy.modules.position_manager import PositionManager
from trend_reversal_strategy.modules.visualizer import StrategyVisualizer
from trend_reversal_strategy.modules.volume_profile import VolumeProfileAnalyzer
from trend_reversal_strategy.modules.utils import setup_logging, ensure_directory_exists

def main():
    """
    Run the volume profile demonstration.
    """
    # Set up logging
    setup_logging()
    
    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    ensure_directory_exists(output_dir)
    
    # Load market data
    df = load_market_data(config.SYMBOL, config.INTERVAL, config.LOOKBACK_DAYS)
    
    # Preprocess data
    df = preprocess_data(df)
    
    # Add technical indicators
    df = add_all_indicators(df, config)
    
    # Generate signals
    strategy = TrendReversalStrategy(config)
    df = strategy.generate_signals(df)
    df = strategy.filter_signals(df)
    
    # Backtest positions
    position_manager = PositionManager(config)
    position1_results, position2_results, combined_results, position1_metrics, position2_metrics = position_manager.backtest_positions(df)
    
    # Initialize volume profile analyzer
    volume_analyzer = VolumeProfileAnalyzer(price_precision=0.005)
    
    # For hourly data, we'll only analyze the last N days
    plot_days = config.PLOT_DAYS
    hours_to_plot = plot_days * 24
    plot_start_idx = max(0, len(df) - hours_to_plot)
    plot_df = df.iloc[plot_start_idx:]
    
    # Calculate volume profile
    volume_profile, key_levels = volume_analyzer.analyze(plot_df)
    
    # Print key levels
    print("Volume Profile Key Levels:")
    print(f"Point of Control: {key_levels['point_of_control']:.4f}")
    print(f"Value Area High: {key_levels['value_area_high']:.4f}")
    print(f"Value Area Low: {key_levels['value_area_low']:.4f}")
    print(f"VWAP: {key_levels['vwap']:.4f}")
    print(f"High Volume Nodes: {[f'{p:.4f}' for p in key_levels['high_volume_nodes']]}")
    
    # Create enhanced visualization with volume profile
    fig = plt.figure(figsize=(16, 14))
    gs = GridSpec(5, 6, figure=fig)
    
    # Price chart with volume profile
    ax1 = fig.add_subplot(gs[0:2, 0:5])
    ax1.plot(plot_df.index, plot_df['Close'], label=f'Copper Futures Price (Last {plot_days} Days)')
    
    # Plot entry points
    entry_dates = []
    entry_prices = []
    
    # Extract entry points from position results
    for _, row in position1_results.iterrows():
        if row['Entry Date'] in plot_df.index:
            entry_dates.append(row['Entry Date'])
            entry_prices.append(row['Entry Price'])
    
    # Plot entry points
    for i, (date, price) in enumerate(zip(entry_dates, entry_prices)):
        ax1.scatter(date, price, color='green', marker='^', s=100)
    
    # Plot exit points for position 1
    for _, row in position1_results.iterrows():
        if row['Exit Date'] in plot_df.index:
            if row['Exit Reason'] == 'Take Profit':
                ax1.scatter(row['Exit Date'], row['Exit Price'], color='blue', marker='o', s=100)
            elif row['Exit Reason'] == 'Stop Loss':
                ax1.scatter(row['Exit Date'], row['Exit Price'], color='purple', marker='v', s=100)
    
    # Plot exit points for position 2
    for _, row in position2_results.iterrows():
        if row['Exit Date'] in plot_df.index:
            if row['Exit Reason'] == 'Trend Reversal':
                ax1.scatter(row['Exit Date'], row['Exit Price'], color='orange', marker='x', s=100)
            elif row['Exit Reason'] == 'Stop Loss':
                ax1.scatter(row['Exit Date'], row['Exit Price'], color='purple', marker='v', s=100)
    
    # Add key levels as horizontal lines
    ax1.axhline(y=key_levels['point_of_control'], color='r', linestyle='-', linewidth=1, alpha=0.7, label='Point of Control')
    ax1.axhline(y=key_levels['value_area_high'], color='g', linestyle='--', linewidth=1, alpha=0.7, label='Value Area High')
    ax1.axhline(y=key_levels['value_area_low'], color='g', linestyle='--', linewidth=1, alpha=0.7, label='Value Area Low')
    
    # Add high volume nodes
    for price in key_levels['high_volume_nodes']:
        ax1.axhline(y=price, color='purple', linestyle=':', linewidth=1, alpha=0.5)
    
    ax1.set_title(f"Copper Futures 1-Hour Price (Last {plot_days} Days) with Volume Profile Key Levels")
    ax1.legend(loc='upper left')
    
    # Volume profile on the right
    ax_vol = fig.add_subplot(gs[0:2, 5])
    volume_analyzer.plot_volume_profile(volume_profile, key_levels, ax=ax_vol)
    ax_vol.set_ylabel('')  # Remove y-label as it's redundant
    
    # Primary MACD
    ax2 = fig.add_subplot(gs[2, 0:6])
    ax2.plot(plot_df.index, plot_df['macd_p'], 
             label=f'MACD Primary ({config.PRIMARY_MACD_FAST},{config.PRIMARY_MACD_SLOW},{config.PRIMARY_MACD_SIGNAL})')
    ax2.plot(plot_df.index, plot_df['signal_p'], label='Signal Primary')
    ax2.bar(plot_df.index, plot_df['macd_diff_p'], color='gray', alpha=0.3, label='MACD Histogram')
    
    # Highlight bullish and bearish trend reversal points
    bullish_reversal_dates = plot_df[plot_df['bullish_reversal'] == True].index
    bearish_reversal_dates = plot_df[plot_df['bearish_reversal'] == True].index
    
    for date in bullish_reversal_dates:
        ax2.axvline(x=date, color='green', linestyle='--', alpha=0.5)
        
    for date in bearish_reversal_dates:
        ax2.axvline(x=date, color='red', linestyle='--', alpha=0.5)
        
    ax2.set_title(f"Primary MACD ({config.PRIMARY_MACD_FAST},{config.PRIMARY_MACD_SLOW},{config.PRIMARY_MACD_SIGNAL}) "
                 f"with Bullish/Bearish Trend Reversals")
    ax2.legend()
    
    # Secondary MACD
    ax3 = fig.add_subplot(gs[3, 0:6])
    ax3.plot(plot_df.index, plot_df['macd_f'], 
             label=f'MACD Fast ({config.SECONDARY_MACD_FAST},{config.SECONDARY_MACD_SLOW},{config.SECONDARY_MACD_SIGNAL})')
    ax3.plot(plot_df.index, plot_df['signal_f'], label='Signal Fast')
    ax3.bar(plot_df.index, plot_df['macd_diff_f'], color='gray', alpha=0.3, label='MACD Histogram')
    
    # Highlight crossover points
    cross_up_dates = plot_df[plot_df['f_cross_up'] == True].index
    cross_down_dates = plot_df[plot_df['f_cross_down'] == True].index
    
    for date in cross_up_dates:
        ax3.axvline(x=date, color='green', linestyle='--', alpha=0.5)
        
    for date in cross_down_dates:
        ax3.axvline(x=date, color='red', linestyle='--', alpha=0.5)
        
    ax3.set_title(f"Secondary MACD ({config.SECONDARY_MACD_FAST},{config.SECONDARY_MACD_SLOW},{config.SECONDARY_MACD_SIGNAL}) "
                 f"with Crossovers")
    ax3.legend()
    
    # Volume
    ax4 = fig.add_subplot(gs[4, 0:6])
    ax4.bar(plot_df.index, plot_df['Volume'], color='blue', alpha=0.5, label='Volume')
    ax4.set_title("Volume")
    ax4.legend()
    
    plt.tight_layout()
    
    # Save the figure
    output_path = os.path.join(output_dir, 'volume_profile_integration.png')
    plt.savefig(output_path)
    print(f"Chart saved to {output_path}")
    
    # Print performance summary
    visualizer = StrategyVisualizer(config)
    visualizer.print_performance_summary(combined_results, position1_metrics, position2_metrics)

if __name__ == "__main__":
    main()