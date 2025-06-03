"""
Run the strategy with different parameter combinations to find optimal settings.
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import itertools
from datetime import datetime

# Import configuration
from trend_reversal_strategy import config

# Import modules
from trend_reversal_strategy.modules.data_loader import load_market_data, preprocess_data
from trend_reversal_strategy.modules.indicators import add_all_indicators
from trend_reversal_strategy.modules.strategy import TrendReversalStrategy
from trend_reversal_strategy.modules.position_manager import PositionManager
from trend_reversal_strategy.modules.visualizer import StrategyVisualizer
from trend_reversal_strategy.modules.utils import setup_logging, ensure_directory_exists

def run_parameter_test(symbol, interval, lookback_days, 
                      primary_macd_params, secondary_macd_params, 
                      risk_reward_ratio, stop_loss_buffer):
    """
    Run the strategy with a specific set of parameters.
    
    Args:
        symbol (str): Symbol to trade
        interval (str): Data interval
        lookback_days (int): Number of days to look back
        primary_macd_params (tuple): (fast, slow, signal) for primary MACD
        secondary_macd_params (tuple): (fast, slow, signal) for secondary MACD
        risk_reward_ratio (float): Risk-reward ratio for take profit
        stop_loss_buffer (float): Buffer for stop loss
        
    Returns:
        dict: Performance metrics
    """
    # Override config parameters
    config.PRIMARY_MACD_FAST = primary_macd_params[0]
    config.PRIMARY_MACD_SLOW = primary_macd_params[1]
    config.PRIMARY_MACD_SIGNAL = primary_macd_params[2]
    
    config.SECONDARY_MACD_FAST = secondary_macd_params[0]
    config.SECONDARY_MACD_SLOW = secondary_macd_params[1]
    config.SECONDARY_MACD_SIGNAL = secondary_macd_params[2]
    
    config.RISK_REWARD_RATIO = risk_reward_ratio
    config.STOP_LOSS_BUFFER = stop_loss_buffer
    
    # Load and process data
    df = load_market_data(symbol, interval, lookback_days)
    df = preprocess_data(df)
    df = add_all_indicators(df, config)
    
    # Generate signals
    strategy = TrendReversalStrategy(config)
    df = strategy.generate_signals(df)
    df = strategy.filter_signals(df)
    
    # Backtest positions
    position_manager = PositionManager(config)
    position1_results, position2_results, combined_results, position1_metrics, position2_metrics = position_manager.backtest_positions(df)
    
    # Create parameter string for identification
    param_str = f"P{primary_macd_params[0]}-{primary_macd_params[1]}-{primary_macd_params[2]}_" \
                f"S{secondary_macd_params[0]}-{secondary_macd_params[1]}-{secondary_macd_params[2]}_" \
                f"RR{risk_reward_ratio}_SL{stop_loss_buffer}"
    
    # Return results with parameter info
    return {
        'parameters': param_str,
        'primary_macd': primary_macd_params,
        'secondary_macd': secondary_macd_params,
        'risk_reward': risk_reward_ratio,
        'stop_loss_buffer': stop_loss_buffer,
        'total_trades': combined_results['total_trades'],
        'total_return': combined_results['total_return'],
        'win_rate': combined_results['win_rate'],
        'avg_return': combined_results['avg_return'],
        'position1_return': position1_metrics['total_return'],
        'position1_win_rate': position1_metrics['win_rate'],
        'position2_return': position2_metrics['total_return'],
        'position2_win_rate': position2_metrics['win_rate']
    }

def main():
    """
    Run parameter optimization.
    """
    # Set up logging
    setup_logging()
    
    # Parameter combinations to test
    primary_macd_params = [
        (6, 13, 4),  # Current
        (8, 17, 5),  # Slower
        (5, 10, 3)   # Faster
    ]
    
    secondary_macd_params = [
        (3, 7, 3),   # Current
        (4, 9, 4),   # Slower
        (2, 5, 2)    # Faster
    ]
    
    risk_reward_ratios = [1.0, 1.2, 1.5, 2.0]
    stop_loss_buffers = [0.002, 0.003, 0.005]
    
    # Fixed parameters
    symbol = config.SYMBOL
    interval = config.INTERVAL
    lookback_days = config.LOOKBACK_DAYS
    
    # Store results
    results = []
    
    # Generate all combinations
    param_combinations = list(itertools.product(
        primary_macd_params, 
        secondary_macd_params, 
        risk_reward_ratios, 
        stop_loss_buffers
    ))
    
    total_combinations = len(param_combinations)
    print(f"Testing {total_combinations} parameter combinations...")
    
    # Run tests
    for i, (primary, secondary, rr, sl) in enumerate(param_combinations):
        print(f"Running combination {i+1}/{total_combinations}: "
              f"Primary MACD {primary}, Secondary MACD {secondary}, "
              f"RR {rr}, SL Buffer {sl}")
        
        try:
            result = run_parameter_test(
                symbol, interval, lookback_days,
                primary, secondary, rr, sl
            )
            results.append(result)
            
            # Print interim results
            print(f"  Total Return: {result['total_return']*100:.2f}%, "
                  f"Win Rate: {result['win_rate']*100:.2f}%, "
                  f"Trades: {result['total_trades']}")
            
        except Exception as e:
            print(f"Error with combination {i+1}: {e}")
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    # Sort by total return
    results_df = results_df.sort_values('total_return', ascending=False)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    ensure_directory_exists(output_dir)
    
    results_file = os.path.join(output_dir, f"optimization_results_{timestamp}.csv")
    results_df.to_csv(results_file, index=False)
    
    # Print top 5 results
    print("\nTop 5 Parameter Combinations by Total Return:")
    print(results_df.head(5)[['parameters', 'total_trades', 'total_return', 'win_rate', 'avg_return']])
    
    # Print top 5 by win rate with at least 20 trades
    print("\nTop 5 Parameter Combinations by Win Rate (min 20 trades):")
    win_rate_df = results_df[results_df['total_trades'] >= 20].sort_values('win_rate', ascending=False)
    print(win_rate_df.head(5)[['parameters', 'total_trades', 'total_return', 'win_rate', 'avg_return']])
    
    print(f"\nResults saved to {results_file}")

if __name__ == "__main__":
    main()