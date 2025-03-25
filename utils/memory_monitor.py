"""
Memory usage monitoring utility
"""
import os
import gc
from utils.logger import setup_logger

# Try to import psutil, but provide fallbacks if it's not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger = setup_logger(__name__)
    logger.warning("psutil package not available. Memory monitoring will be limited.")
    logger.warning("Install psutil with: pip install psutil")

logger = setup_logger(__name__)

def get_process_memory():
    """
    Get current memory usage of the process in MB
    
    Returns:
        float: Memory usage in MB
    """
    if not PSUTIL_AVAILABLE:
        # If psutil is not available, trigger garbage collection and return a placeholder
        gc.collect()
        return 0.0  # Just return 0 since we can't measure
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # Return in MB
    return memory_info.rss / (1024 * 1024)

def log_memory_usage():
    """
    Log current memory usage
    """
    memory_mb = get_process_memory()
    logger.info(f"Current memory usage: {memory_mb:.2f} MB")

def clean_memory():
    """
    Attempt to free up memory
    """
    before = get_process_memory()
    
    # Force garbage collection
    gc.collect()
    
    # Get memory after cleanup
    after = get_process_memory()
    
    logger.info(f"Memory cleanup: {before:.2f} MB -> {after:.2f} MB (freed {before - after:.2f} MB)")
    
    return before - after

def memory_warning_check(threshold_mb=1000):
    """
    Check if memory usage exceeds threshold
    
    Args:
        threshold_mb (int): Memory threshold in MB
        
    Returns:
        bool: True if memory usage exceeds threshold
    """
    if not PSUTIL_AVAILABLE:
        # If psutil is not available, we can't check memory
        # but we'll trigger garbage collection as a precaution
        gc.collect()
        return False
    
    memory_mb = get_process_memory()
    
    if memory_mb > threshold_mb:
        logger.warning(f"Memory usage high: {memory_mb:.2f} MB (threshold: {threshold_mb} MB)")
        return True
    
    return False