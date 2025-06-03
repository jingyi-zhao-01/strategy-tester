"""
Utility functions for the trading strategy.
"""

import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Set up logging configuration.
    
    Args:
        log_level (int): Logging level
        log_file (str): Path to log file
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if log_file:
        logging.basicConfig(level=log_level, format=log_format, filename=log_file)
    else:
        logging.basicConfig(level=log_level, format=log_format)
    
    # Reduce verbosity of third-party libraries
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('yfinance').setLevel(logging.WARNING)

def ensure_directory_exists(directory):
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory (str): Directory path
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def get_timestamp_string():
    """
    Get a timestamp string for file naming.
    
    Returns:
        str: Timestamp string in format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def save_results_to_csv(position1_results, position2_results, output_dir):
    """
    Save trade results to CSV files.
    
    Args:
        position1_results (pandas.DataFrame): Position 1 results
        position2_results (pandas.DataFrame): Position 2 results
        output_dir (str): Output directory
    """
    ensure_directory_exists(output_dir)
    
    timestamp = get_timestamp_string()
    
    position1_file = os.path.join(output_dir, f"position1_results_{timestamp}.csv")
    position2_file = os.path.join(output_dir, f"position2_results_{timestamp}.csv")
    
    position1_results.to_csv(position1_file, index=False)
    position2_results.to_csv(position2_file, index=False)
    
    logger.info(f"Saved position 1 results to {position1_file}")
    logger.info(f"Saved position 2 results to {position2_file}")
    
    return position1_file, position2_file