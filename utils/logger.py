"""
Logger utility for the LinkedIn Recruiting Bot
"""
import logging
import sys
import os
import io
from pathlib import Path

# Default log file location if config not available
DEFAULT_LOG_FILE = os.path.join(Path(__file__).resolve().parent.parent, "logs", "bot.log")

def setup_logger(name):
    """
    Set up a logger with file and console handlers
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: Configured logger
    """
    # Make sure logs directory exists
    log_dir = os.path.dirname(DEFAULT_LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Only add handlers if they don't exist
    if not logger.handlers:
        try:
            # Create file handler with UTF-8 encoding
            file_handler = logging.FileHandler(DEFAULT_LOG_FILE, encoding='utf-8')
            
            # Create console handler with special encoding for Windows
            if sys.platform == 'win32':
                # Wrap sys.stdout with a writer that uses utf-8 encoding
                try:
                    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
                    console_handler = logging.StreamHandler(utf8_stdout)
                except Exception as e:
                    # Fallback if wrapping fails
                    print(f"Warning: Unicode wrapping failed ({e}). Some characters may not display correctly.")
                    console_handler = logging.StreamHandler(sys.stdout)
            else:
                console_handler = logging.StreamHandler(sys.stdout)
            
            # Create formatters
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            # Set formatters
            file_handler.setFormatter(file_formatter)
            console_handler.setFormatter(console_formatter)
            
            # Add handlers
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        except Exception as e:
            print(f"Error setting up logger: {e}")
            # Add at least a console handler
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(ch)
    
    return logger