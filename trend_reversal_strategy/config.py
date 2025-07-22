"""
Configuration settings for the Trend Reversal Trading Strategy.
"""
# Gold: GC=F
# Silver: SI=F
# Crude Oil (WTI): CL=F
# Natural Gas: NG=F
# S&P 500 E-mini: ES=F
# Nasdaq 100 E-mini: NQ=F
# Dow Jones E-mini: YM=F
# Corn: ZC=F
# Soybeans: ZS=F
# Wheat: ZW=F
# Coffee: KC=F
# Platinum: PL=F
# Palladium: PA=F
# Heating Oil: HO=F
# Gasoline: RB=F
# Euro FX: 6E=F
# Japanese Yen: 6J=F

# Data settings
SYMBOL = "ZS=F"  # Copper Futures
INTERVAL = "1h"  # 1-hour data
LOOKBACK_DAYS = 360  # Number of days to look back for data

# MACD parameters
# Primary MACD (slower, for trend detection)
PRIMARY_MACD_FAST = 12
PRIMARY_MACD_SLOW = 26
PRIMARY_MACD_SIGNAL =9

# Secondary MACD (faster, for entry signals)
SECONDARY_MACD_FAST = 5
SECONDARY_MACD_SLOW = 13
SECONDARY_MACD_SIGNAL = 5

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
RISK_REWARD_RATIO = 2       # Risk-reward ratio for take profit 2X

# Visualization
PLOT_DAYS = LOOKBACK_DAYS  # Number of days to show in the chart
CHART_FILENAME = 'dual_position_strategy_1h.png'  # Output filename
CHART_SIZE = (16, 12)  # Chart size in inches