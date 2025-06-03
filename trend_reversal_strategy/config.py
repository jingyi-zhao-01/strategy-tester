"""
Configuration settings for the Trend Reversal Trading Strategy.
"""

# Data settings
SYMBOL = "HG=F"  # Copper Futures
INTERVAL = "1h"  # 1-hour data
LOOKBACK_DAYS = 60  # Number of days to look back for data

# MACD parameters
# Primary MACD (slower, for trend detection)
PRIMARY_MACD_FAST = 6
PRIMARY_MACD_SLOW = 13
PRIMARY_MACD_SIGNAL = 4

# Secondary MACD (faster, for entry signals)
SECONDARY_MACD_FAST = 3
SECONDARY_MACD_SLOW = 7
SECONDARY_MACD_SIGNAL = 3

# Slope calculation windows
SHORT_SLOPE_WINDOW = 2  # Short-term slope window (in bars)
LONG_SLOPE_WINDOW = 5   # Long-term slope window (in bars)

# Trend detection parameters
TREND_REVERSAL_LOOKBACK = 12  # Lookback window for trend reversal detection (in bars)
PARALLEL_THRESHOLD = 0.0001   # Threshold for detecting parallel lines
SNAP_THRESHOLD = 0.0002       # Threshold for detecting fast line snap

# Position management
STOP_LOSS_LOOKBACK = 24       # Lookback period for finding recent lows (in bars)
STOP_LOSS_BUFFER = 0.003      # Buffer below recent low (0.3%)
DEFAULT_STOP_LOSS_PCT = 0.01  # Default stop loss percentage (1%)
RISK_REWARD_RATIO = 1.2       # Risk-reward ratio for take profit (1.2x the risk)

# Visualization
PLOT_DAYS = 14  # Number of days to show in the chart
CHART_FILENAME = 'dual_position_strategy_1h.png'  # Output filename
CHART_SIZE = (16, 12)  # Chart size in inches