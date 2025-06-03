"""
Main entry point for the Trend Reversal Trading Strategy.
"""

import os
import logging
import argparse
import pandas as pd
import matplotlib.pyplot as plt

# Import configuration
from trend_reversal_strategy import config

# Import modules
from trend_reversal_strategy.modules.data_loader import load_market_data, preprocess_data
from trend_reversal_strategy.modules.indicators import add_all_indicators
from trend_reversal_strategy.modules.strategy import TrendReversalStrategy
from trend_reversal_strategy.modules.position_manager import PositionManager
from trend_reversal_strategy.modules.visualizer import StrategyVisualizer
from trend_reversal_strategy.modules.utils import setup_logging, ensure_directory_exists, save_results_to_csv

def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Trend Reversal Trading Strategy')
    
    parser.add_argument('--symbol', type=str, default=config.SYMBOL,
                        help=f'Symbol to trade (default: {config.SYMBOL})')
    
    parser.add_argument('--interval', type=str, default=config.INTERVAL,
                        help=f'Data interval (default: {config.INTERVAL})')
    
    parser.add_argument('--lookback', type=int, default=config.LOOKBACK_DAYS,
                        help=f'Number of days to look back (default: {config.LOOKBACK_DAYS})')
    
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Output directory for results and charts')
    
    parser.add_argument('--no-plot', action='store_true',
                        help='Disable plotting')
    
    parser.add_argument('--save-csv', action='store_true',
                        help='Save results to CSV files')
    
    return parser.parse_args()

def run_strategy(args):
    """
    Run the trading strategy.
    
    Args:
        args (argparse.Namespace): Command line arguments
    """
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(__file__), args.output_dir)
    ensure_directory_exists(output_dir)
    
    # Load market data
    df = load_market_data(args.symbol, args.interval, args.lookback)
    
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
    
    # Visualize results
    visualizer = StrategyVisualizer(config)
    
    # Print performance summary
    visualizer.print_performance_summary(combined_results, position1_metrics, position2_metrics)
    
    # Print trade summaries
    print("\nPosition 1 Trade Summary:")
    print(position1_results[['Entry Date', 'Entry Price', 'Exit Date', 'Exit Price', 'Return', 'Exit Reason']])
    
    print("\nPosition 2 Trade Summary:")
    print(position2_results[['Entry Date', 'Entry Price', 'Exit Date', 'Exit Price', 'Return', 'Exit Reason']])
    
    # Save results to CSV if requested
    if args.save_csv:
        save_results_to_csv(position1_results, position2_results, output_dir)
    
    # Plot results if not disabled
    if not args.no_plot:
        output_path = os.path.join(output_dir, config.CHART_FILENAME)
        visualizer.plot_strategy_results(df, position1_results, position2_results, output_path)
        plt.show()
    
    logger.info("Strategy execution completed")

if __name__ == "__main__":
    args = parse_arguments()
    run_strategy(args)