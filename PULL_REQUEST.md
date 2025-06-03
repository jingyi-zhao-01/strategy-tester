# Modular Dual-Position Trend Reversal Strategy for Copper Futures

## Overview

This PR implements a complete refactoring of the copper futures trading strategy into a modular, maintainable structure. The strategy now uses 1-hour interval data instead of daily data and implements a dual position management system with different exit strategies for each position.

## Key Changes

### Modular Structure
- Refactored single-file implementation into a proper package structure
- Created separate modules for data loading, indicators, strategy, position management, and visualization
- Implemented centralized configuration management

### Strategy Enhancements
- Converted to 1-hour interval data (from daily data)
- Adjusted MACD parameters for hourly timeframe:
  - Primary MACD: (6,13,4) instead of (12,26,9)
  - Secondary MACD: (3,7,3) instead of (5,13,5)
- Implemented dual position management:
  - Position 1: Takes profit at 1.2x risk-reward ratio
  - Position 2: Exits on trend reversal signals
- Enhanced stop loss calculation using recent price lows
- Improved visualization with different markers for exit types

### New Features
- Added volume profile analysis for key price levels
- Created parameter optimization framework
- Enhanced performance reporting with detailed metrics by position and exit type
- Added comprehensive documentation

## Performance

The strategy now shows different performance characteristics for each position:
- Position 1 (Take Profit): Higher win rate with smaller average gains
- Position 2 (Trend Reversal): Lower win rate but potential for larger gains

## Future Work

- Further optimize parameters for hourly data
- Enhance volume profile integration for entry/exit decisions
- Implement real-time data feed integration
- Add machine learning for parameter optimization

## Testing

The strategy has been tested on recent copper futures data (last 60 days of hourly data) and produces consistent results. All modules have been verified to work together correctly.

## Screenshots

Charts showing the strategy performance and volume profile integration are included in the output directory.