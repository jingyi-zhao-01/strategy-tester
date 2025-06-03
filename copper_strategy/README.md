# Dual MACD Trend Reversal Strategy

A trading strategy for copper futures that uses dual MACD indicators to identify trend reversals and manage positions with two different exit approaches.

## Strategy Overview

This strategy uses two MACD indicators with different parameter settings:

1. **Primary MACD (6,13,4)**: Used for trend detection and identifying major trend reversals
2. **Secondary MACD (3,7,3)**: Used for entry signals and faster trend changes

The strategy enters trades when the Secondary MACD crosses above its signal line while the Primary MACD indicates a bullish trend. It then manages two separate positions with different exit strategies:

- **Position 1**: Uses a fixed risk-reward ratio (1.2x) for take profit, with a stop loss based on recent price lows
- **Position 2**: Exits when the trend reverses (Secondary MACD crosses below signal line or Primary MACD shows a bearish reversal)

## Features

- Dual position management with different exit strategies
- Dynamic stop loss calculation based on recent price lows
- Take profit targets based on risk-reward ratio
- Trend reversal detection using MACD slope analysis
- Comprehensive visualization of signals and performance
- Detailed performance metrics by exit reason

## Directory Structure

```
trend_reversal_strategy/
├── __init__.py
├── config.py           # Configuration settings
├── main.py             # Main entry point
├── README.md           # Documentation
├── modules/
│   ├── __init__.py
│   ├── data_loader.py        # Data loading and preprocessing
│   ├── indicators.py         # Technical indicators
│   ├── strategy.py           # Signal generation
│   ├── position_manager.py   # Position management
│   ├── visualizer.py         # Visualization
│   └── utils.py              # Utility functions
└── output/                   # Charts and results
```

## Usage

Run the strategy with default settings:

```bash
python -m trend_reversal_strategy.main
```

Customize parameters:

```bash
python -m trend_reversal_strategy.main --symbol "HG=F" --interval "1h" --lookback 60 --save-csv
```

## Parameters

The strategy parameters can be customized in `config.py`:

- **MACD Parameters**: Adjust the windows for both MACD indicators
- **Slope Windows**: Change the sensitivity of trend detection
- **Stop Loss Settings**: Modify the stop loss calculation
- **Risk-Reward Ratio**: Adjust the take profit target

## Future Extensions

The modular design allows for easy extension with additional features:

- **Volume Profile**: Can be added as a new module to enhance entry/exit decisions
- **Additional Indicators**: Can be integrated into the existing framework
- **Machine Learning**: Signal filtering using ML models could be added

## Performance Metrics

The strategy provides detailed performance metrics:

- Overall performance (total return, win rate, average return)
- Position-specific metrics
- Performance breakdown by exit reason
- Trade-by-trade summary

## Visualization

The strategy generates comprehensive visualizations:

- Price chart with entry/exit points
- Primary and Secondary MACD indicators
- Trend reversal detection
- MACD slope analysis