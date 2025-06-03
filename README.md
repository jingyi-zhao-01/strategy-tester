# Copper Futures Trading Strategy

A modular implementation of a dual-position trend reversal trading strategy for copper futures.

## Overview

This strategy uses a combination of MACD indicators to identify trend reversals and generate trading signals:

- **Primary MACD (6,13,4)**: Used to identify the overall trend direction
- **Secondary MACD (3,7,3)**: Used for entry and exit timing

The strategy implements a dual position management system:
- **Position 1**: Takes profit at a predefined risk-reward ratio (1.2x)
- **Position 2**: Exits on trend reversal signals

## Features

- Hourly data analysis for copper futures
- Dual position management with different exit strategies
- Stop loss calculation based on recent price lows
- Take profit mechanism for position 1
- Trend reversal exit for position 2
- Comprehensive performance metrics
- Volume profile analysis for key price levels
- Parameter optimization capabilities

## Directory Structure

```
trend_reversal_strategy/
├── config.py                # Configuration settings
├── main.py                  # Main entry point
├── modules/
│   ├── data_loader.py       # Data loading and preprocessing
│   ├── indicators.py        # Technical indicators
│   ├── position_manager.py  # Position management
│   ├── strategy.py          # Signal generation
│   ├── utils.py             # Utility functions
│   ├── visualizer.py        # Visualization
│   └── volume_profile.py    # Volume profile analysis
├── output/                  # Output charts and results
├── run_optimization.py      # Parameter optimization
└── volume_profile_demo.py   # Volume profile integration demo
```

## Usage

Run the main strategy:
```
python -m trend_reversal_strategy.main
```

Run with volume profile analysis:
```
python -m trend_reversal_strategy.volume_profile_demo
```

Run parameter optimization:
```
python -m trend_reversal_strategy.run_optimization
```

## Performance

The strategy is designed to:
- Capture short-term trend reversals in copper futures
- Manage risk with dynamic stop losses
- Take profits at predefined levels for position 1
- Hold position 2 for longer-term trend moves

## Future Enhancements

- Integration with real-time data feeds
- Enhanced volume profile analysis
- Machine learning for parameter optimization
- Additional technical indicators
- Risk management improvements