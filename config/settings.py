"""
Configuration settings for the LinkedIn Recruiting Bot
"""
import os
from pathlib import Path

# Project base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directory
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Logs directory
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# CSV file paths
CSV_PATH = os.path.join(DATA_DIR, "linkedin_recruiting_posts.csv")
CONNECTIONS_CSV_PATH = os.path.join(DATA_DIR, "linkedin_connections.csv")
STATS_CSV_PATH = os.path.join(DATA_DIR, "linkedin_stats.csv")

# Log file path
LOG_FILE = os.path.join(LOGS_DIR, "bot.log")

# Browser settings
HEADLESS = False  # Set to True to run browser in headless mode
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# LinkedIn URLs
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_BASE_URL = "https://www.linkedin.com"

# Fribl messages to append to comments
APPEND_FRIBL_LINK = True  # Set to False to disable appending Fribl messages
FRIBL_BASE_LINK = "https://www.app.fribl.co/login"  # Link to add after Fribl messages


# Fribl links with "It's Free btw" message in different languages
FRIBL_LINK_EN = f"It's Free btw {FRIBL_BASE_LINK}"
FRIBL_LINK_FR = f"C'est Gratuit au fait {FRIBL_BASE_LINK}"
FRIBL_LINK_ES = f"Es Gratis por cierto {FRIBL_BASE_LINK}"


FRIBL_LINK = FRIBL_LINK_EN


# Bot behavior settings
MIN_WAIT_TIME = 2  # Minimum wait time in seconds
MAX_WAIT_TIME = 5  # Maximum wait time in seconds
MIN_TYPE_DELAY = 0.05  # Minimum typing delay in seconds
MAX_TYPE_DELAY = 0.25  # Maximum typing delay in seconds
SCROLL_COUNT = 5  # Number of scrolls to perform when loading posts

# Post filtering settings
MAX_POST_AGE_DAYS = 30  # Maximum age of posts in days

# AI model settings
AI_MODEL = "mistral:latest"  # Changed to use latest version without specific size
AI_TIMEOUT = 40  # Timeout for AI model in seconds

# Connection settings
CONNECTION_WEEKLY_LIMIT = 100  # Maximum number of connection requests per week

# Debug settings
DEBUG_MODE = True  # Set to False in production
HTML_DUMP_DIR = os.path.join(BASE_DIR, "debug", "html")


# Directory structure for review workflow
DATA_DIR = os.path.join(BASE_DIR, "data")
REVIEW_DIR = os.path.join(DATA_DIR, "1.to_review")
TO_SEND_DIR = os.path.join(DATA_DIR, "2.to_send") 
TO_CONNECT_DIR = os.path.join(DATA_DIR, "3.to_connect")
ARCHIVED_DIR = os.path.join(DATA_DIR, "archived")
STATS_DIR = os.path.join(DATA_DIR, "stats")

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REVIEW_DIR, exist_ok=True)
os.makedirs(TO_SEND_DIR, exist_ok=True)
os.makedirs(TO_CONNECT_DIR, exist_ok=True)
os.makedirs(ARCHIVED_DIR, exist_ok=True)
os.makedirs(STATS_DIR, exist_ok=True)

# CSV file paths
CSV_PATH = os.path.join(DATA_DIR, "linkedin_recruiting_posts.csv")
CONNECTIONS_CSV_PATH = os.path.join(STATS_DIR, "linkedin_connections.csv")
STATS_CSV_PATH = os.path.join(STATS_DIR, "linkedin_stats.csv")

# Daily limits
DAILY_COMMENT_LIMIT = 30  # Max number of comments per day
DAILY_CONNECTION_LIMIT = 8  # Max number of connection requests per day