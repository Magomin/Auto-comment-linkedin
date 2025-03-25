"""
Date parsing utilities for LinkedIn post dates
"""
import re
import datetime
from config.settings import MAX_POST_AGE_DAYS

def is_post_within_time_limit(post_date_text):
    """
    Check if the post is within the defined time limit based on LinkedIn's relative date text
    
    Args:
        post_date_text (str): LinkedIn's date text (e.g., "2d", "1w", "3h")
        
    Returns:
        bool: True if the post is within time limit, False otherwise
    """
    today = datetime.datetime.now()
    
    # Common LinkedIn date patterns
    # Hours or minutes (e.g., "2h", "5m")
    if 'h' in post_date_text or 'm' in post_date_text:
        return True
    
    # Days (e.g., "2d")
    elif 'd' in post_date_text:
        match = re.search(r'(\d+)d', post_date_text)
        if match:
            days = int(match.group(1))
            return days <= MAX_POST_AGE_DAYS
    
    # Weeks (e.g., "1w")
    elif 'w' in post_date_text:
        match = re.search(r'(\d+)w', post_date_text)
        if match:
            weeks = int(match.group(1))
            return weeks * 7 <= MAX_POST_AGE_DAYS
    
    # Months (e.g., "1mo")
    elif 'mo' in post_date_text:
        match = re.search(r'(\d+)mo', post_date_text)
        if match:
            months = int(match.group(1))
            # Approximate a month as 30 days
            return months * 30 <= MAX_POST_AGE_DAYS
    
    # Try to parse specific dates (e.g., "Jan 15")
    else:
        try:
            date_formats = ["%b %d", "%B %d"]
            for format in date_formats:
                try:
                    date_obj = datetime.datetime.strptime(post_date_text, format)
                    # Add current year (LinkedIn doesn't show year for recent posts)
                    date_obj = date_obj.replace(year=today.year)
                    
                    # If the resulting date is in the future, it's probably from last year
                    if date_obj > today:
                        date_obj = date_obj.replace(year=today.year - 1)
                    
                    delta = today - date_obj
                    return delta.days <= MAX_POST_AGE_DAYS
                except ValueError:
                    continue
        except Exception:
            pass
    
    # Default to False if we can't determine the date
    return False

def get_standard_date():
    """
    Get the current date in standard format
    
    Returns:
        str: Current date in YYYY-MM-DD format
    """
    return datetime.datetime.now().strftime("%Y-%m-%d")