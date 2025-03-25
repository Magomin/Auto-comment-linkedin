#!/usr/bin/env python3
"""
Entry point for LinkedIn Recruiting Bot with optimized multi-keyword support
"""
import os
import sys
import argparse
import datetime
import gc
from utils.logger import setup_logger
from src.bot import LinkedInRecruitingBot
from src.storage.csv_handler import CSVHandler
from src.keywords import get_keywords
from config import settings
from config.settings import APPEND_FRIBL_LINK, FRIBL_LINK

logger = setup_logger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="LinkedIn Recruiting Bot")
    parser.add_argument("--fetch", action="store_true",
                        help="Search for posts and generate review files")
    parser.add_argument("--send_comments", action="store_true",
                        help="Send comments from ready-to-send files (renamed from --send)")
    parser.add_argument("--fetch-and-send", action="store_true",
                        help="Fetch posts and send ready comments")
    parser.add_argument("--stats", action="store_true",
                        help="Generate and display statistics report")
    parser.add_argument("--limit", type=int, default=30,
                        help="Limit the number of posts/comments/connections/keywords to process (default: 30)")
    parser.add_argument("--debug", "-d", action="store_true",
                        help="Enable debug mode with screenshots and HTML dumps")
    parser.add_argument("--headless", action="store_true",
                        help="Run in headless mode (no browser UI)")
    parser.add_argument("--language", type=str, default="en", choices=["en", "fr", "es", "all"],
                        help="Language for keywords (en, fr, es, all)")
    parser.add_argument("--batch-size", type=int, default=5,
                        help="Number of keywords to process before restarting browser (default: 5)")
    parser.add_argument("--keywords", type=str,
                        help="Comma-separated list of keywords to use instead of defaults")
    return parser.parse_args()

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        # Check for Ollama
        import subprocess
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        
        # Check if required model is available
        model_name = settings.AI_MODEL.split(":")[0]
        if model_name not in result.stdout.lower():
            logger.warning(f"{model_name} model not found in Ollama. You may need to run: ollama pull {settings.AI_MODEL}")
        
        # Check for Python dependencies
        import pandas as pd
        from selenium import webdriver
        
        return True
    except FileNotFoundError:
        logger.error("Ollama not found. Please install Ollama: https://ollama.ai/download")
        return False
    except ImportError as e:
        logger.error(f"Missing Python dependency: {e}")
        logger.error("Please install required packages: pip install -r requirements.txt")
        return False

def check_credentials():
    """Check if LinkedIn credentials are configured"""
    try:
        from config.credentials import LINKEDIN_USERNAME, LINKEDIN_PASSWORD
        
        if not LINKEDIN_USERNAME or not LINKEDIN_PASSWORD:
            logger.error("LinkedIn credentials not configured. Please update config/credentials.py")
            return False
        
        if LINKEDIN_USERNAME == "your_linkedin_email@example.com":
            logger.error("LinkedIn credentials not configured. Please update config/credentials.py")
            return False
        
        return True
    except ImportError:
        logger.error("Credentials file not found. Please create config/credentials.py from the template.")
        return False

def export_comments_to_text(csv_path):
    """
    Export comments from CSV to a text file for review
    
    Args:
        csv_path (str): Path to the CSV file
        
    Returns:
        str: Path to the created text file
    """
    try:
        import pandas as pd
        from config.settings import APPEND_FRIBL_LINK, FRIBL_LINK 
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(csv_path), "exports")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create output filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"comments_export_{timestamp}.txt")
        
        # Load CSV file
        df = pd.read_csv(csv_path)
        
        # Check if dataframe is empty
        if df.empty:
            logger.error("No data found in CSV file")
            return None
        
        # Write to text file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("LinkedIn Recruiting Bot - Comments Export\n")
            f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 80 + "\n\n")
            
            # Add summary statistics
            stats_handler = CSVHandler()
            stats = stats_handler.get_stats_summary(days=7)
            
            f.write("SUMMARY STATISTICS (LAST 7 DAYS)\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total posts found: {stats['total_posts_found']}\n")
            f.write(f"Total comments posted: {stats['total_comments_posted']}\n")
            f.write(f"Total connections sent: {stats['total_connections_sent']}\n")
            f.write(f"All-time comments: {stats['all_time_comments']}\n")
            f.write(f"All-time connections: {stats['all_time_connections']}\n")
            f.write("-" * 40 + "\n\n")
            
            # Add keyword statistics if available
            if stats['keywords_stats']:
                f.write("KEYWORDS PERFORMANCE\n")
                f.write("-" * 40 + "\n")
                for keyword, kw_stats in stats['keywords_stats'].items():
                    f.write(f"Keyword: {keyword}\n")
                    f.write(f"  Posts found: {kw_stats['posts_found']}\n")
                    f.write(f"  Comments posted: {kw_stats['comments_posted']}\n")
                    f.write(f"  Connections sent: {kw_stats['connections_sent']}\n")
                f.write("-" * 40 + "\n\n")
            
            # Add language statistics if available
            if stats['languages_stats']:
                f.write("LANGUAGE PERFORMANCE\n")
                f.write("-" * 40 + "\n")
                for language, lang_stats in stats['languages_stats'].items():
                    f.write(f"Language: {language}\n")
                    f.write(f"  Posts found: {lang_stats['posts_found']}\n")
                    f.write(f"  Comments posted: {lang_stats['comments_posted']}\n")
                    f.write(f"  Connections sent: {lang_stats['connections_sent']}\n")
                f.write("-" * 40 + "\n\n")
            
            # Weekly connection limit
            weekly_connections = stats_handler.get_weekly_connection_count()
            f.write(f"Weekly connection requests: {weekly_connections}/{settings.CONNECTION_WEEKLY_LIMIT}\n\n")
            
            f.write("=" * 80 + "\n\n")
            
            # Write individual entries
            for i, row in df.iterrows():
                f.write(f"Entry #{i+1}\n")
                f.write(f"Lead name: {row.get('author_name', 'Unknown')}\n")
                f.write(f"Post URL: {row.get('post_url', 'Unknown')}\n")
                f.write(f"Post date: {row.get('post_date', 'Unknown')}\n")
                f.write(f"Language: {row.get('language', 'Unknown')}\n")
                
                # Show comment status
                comment_status = row.get('comment_status', 'pending')
                commented_at = row.get('commented_at', '')
                status_text = f"{comment_status.upper()}"
                if commented_at:
                    status_text += f" ({commented_at})"
                f.write(f"Comment status: {status_text}\n")
                
                # Show connection status if available
                connection_requested = row.get('connection_requested', 'false')
                if connection_requested.lower() == 'true':
                    f.write(f"Connection status: {row.get('connection_status', 'Unknown')}\n")
                
                # Check if the post has useful content
                post_content = row.get('post_content', '').strip()
                if post_content:
                    f.write("\nPOST CONTENT:\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"{post_content}\n")
                    f.write("-" * 40 + "\n")
                else:
                    f.write("\nPOST CONTENT: [Empty or not available]\n")
                
                # Write the comment section
                f.write("\nCOMMENT:\n")
                f.write("-" * 40 + "\n")
                f.write(f"{row.get('comment', 'No comment generated')}\n")
                f.write("-" * 40 + "\n")
                
                # Add verification info
                verification = row.get('verification', 'Unknown')
                f.write(f"Comment Type: {verification}\n")
                
                # Check for Fribl mentions to highlight good generations
                comment = row.get('comment', '').lower()
                if "fribl" in comment and "ai" in verification.lower():
                    f.write("✓ AI successfully included Fribl reference\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
                
        logger.info(f"Successfully exported comments to: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error exporting comments to text: {e}")
        return None

def generate_report():
    """Generate a comprehensive report of bot activity"""
    csv_handler = CSVHandler()
    output_file = export_comments_to_text(csv_handler.csv_path)
    if output_file:
        logger.info(f"Successfully exported report to: {output_file}")
        # Open the file with default text editor on most systems
        try:
            if sys.platform == 'win32':
                os.startfile(output_file)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{output_file}"')
            else:  # Linux
                os.system(f'xdg-open "{output_file}"')
            logger.info("Report opened for review")
        except Exception as e:
            logger.warning(f"Could not automatically open the report: {e}")
        return True
    return False

def generate_stats_report(days=7):
    """
    Generate a statistics report
    
    Args:
        days (int, optional): Number of days to include in the report. Defaults to 7.
        
    Returns:
        str: Path to the generated stats file
    """
    try:
        # Create stats directory if it doesn't exist
        os.makedirs(settings.STATS_DIR, exist_ok=True)
        
        # Create output filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(settings.STATS_DIR, f"linkedin_stats_{timestamp}.txt")
        
        # Get statistics
        csv_handler = CSVHandler()
        stats = csv_handler.get_stats_summary(days=days)
        
        # Write to text file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("LinkedIn Recruiting Bot - Statistics Report\n")
            f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Period: Last {days} days\n")
            f.write("-" * 80 + "\n\n")
            
            f.write("SUMMARY STATISTICS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total posts found: {stats['total_posts_found']}\n")
            f.write(f"Total comments posted: {stats['total_comments_posted']}\n")
            f.write(f"Total connections sent: {stats['total_connections_sent']}\n")
            f.write(f"All-time comments: {stats['all_time_comments']}\n")
            f.write(f"All-time connections: {stats['all_time_connections']}\n")
            f.write("-" * 40 + "\n\n")
            
            # Add keyword statistics if available
            if stats['keywords_stats']:
                f.write("KEYWORDS PERFORMANCE\n")
                f.write("-" * 40 + "\n")
                for keyword, kw_stats in stats['keywords_stats'].items():
                    f.write(f"Keyword: {keyword}\n")
                    f.write(f"  Posts found: {kw_stats['posts_found']}\n")
                    f.write(f"  Comments posted: {kw_stats['comments_posted']}\n")
                    f.write(f"  Connections sent: {kw_stats['connections_sent']}\n")
                f.write("-" * 40 + "\n\n")
            
            # Add language statistics if available
            if stats['languages_stats']:
                f.write("LANGUAGE PERFORMANCE\n")
                f.write("-" * 40 + "\n")
                for language, lang_stats in stats['languages_stats'].items():
                    f.write(f"Language: {language}\n")
                    f.write(f"  Posts found: {lang_stats['posts_found']}\n")
                    f.write(f"  Comments posted: {lang_stats['comments_posted']}\n")
                    f.write(f"  Connections sent: {lang_stats['connections_sent']}\n")
                f.write("-" * 40 + "\n\n")
            
            # Add daily statistics if available
            if stats['daily_stats']:
                f.write("DAILY ACTIVITY\n")
                f.write("-" * 40 + "\n")
                for day_stats in stats['daily_stats']:
                    f.write(f"Date: {day_stats['date']}\n")
                    f.write(f"  Posts found: {day_stats['posts_found']}\n")
                    f.write(f"  Comments posted: {day_stats['comments_posted']}\n")
                    f.write(f"  Connections sent: {day_stats['connections_sent']}\n")
                f.write("-" * 40 + "\n\n")
            
            # Weekly connection limit
            weekly_connections = csv_handler.get_weekly_connection_count()
            f.write(f"Weekly connection requests: {weekly_connections}/{settings.CONNECTION_WEEKLY_LIMIT}\n")
            f.write(f"Daily comment limit: {settings.DAILY_COMMENT_LIMIT}\n")
            f.write(f"Daily connection limit: {settings.DAILY_CONNECTION_LIMIT}\n\n")
            
            f.write("=" * 80 + "\n")
            
        logger.info(f"Generated statistics report: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error generating statistics report: {e}")
        return None

def run_multiple_keywords(self, keywords=None, language="en", batch_size=5):
    """
    Run the bot with multiple keywords, with optimizations to prevent crashes
    
    Args:
        keywords (list, optional): List of keywords to search for. If None, will use default keywords.
        language (str, optional): Language to use for keywords. Defaults to "en".
        batch_size (int, optional): Number of keywords to process before restarting browser. Defaults to 5.
        
    Returns:
        dict: Results containing success rate and details
    """
    import gc  # For garbage collection
    from utils.memory_monitor import log_memory_usage, clean_memory
    from src.keywords import get_keywords
    import time
    import os
    
    # Get keywords if not provided
    if keywords is None:
        keywords = get_keywords(language)
    
    logger.info(f"Starting LinkedIn Recruiting Bot with {len(keywords)} keywords")
    
    # Track results
    results = {
        "total_keywords": len(keywords),
        "successful_searches": 0,
        "failed_searches": 0,
        "total_posts_found": 0,
        "details": {}
    }
    
    try:
        # Process keywords in batches
        for i in range(0, len(keywords), batch_size):
            # Get the current batch of keywords
            batch_keywords = keywords[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} with {len(batch_keywords)} keywords")
            
            # Initialize browser for this batch
            if not self.browser.initialize():
                logger.error("Failed to initialize browser. Aborting batch.")
                continue
            
            # Login to LinkedIn
            if not self.auth.login():
                logger.error("Failed to login to LinkedIn. Aborting batch.")
                self.browser.close()
                continue
            
            # Process each keyword in the batch
            for keyword in batch_keywords:
                try:
                    logger.info(f"Processing keyword: {keyword}")
                    
                    # Clear search field if this is not the first keyword
                    if results["successful_searches"] + results["failed_searches"] > 0:
                        self.search.clear_search_field()
                    
                    # Search and scrape posts for this keyword
                    posts = self.search_and_scrape(keyword)
                    
                    # Update results
                    keyword_success = False
                    if posts:
                        posts_found = len(posts)
                        logger.info(f"Found {posts_found} relevant posts for keyword: {keyword}")
                        results["total_posts_found"] += posts_found
                        keyword_success = True
                    else:
                        logger.warning(f"No relevant posts found for keyword: {keyword}")
                    
                    if keyword_success:
                        results["successful_searches"] += 1
                    else:
                        results["failed_searches"] += 1
                    
                    results["details"][keyword] = {
                        "success": keyword_success,
                        "posts_found": len(posts) if posts else 0
                    }
                    
                    # Force garbage collection
                    gc.collect()
                    
                    # Log memory usage if in debug mode
                    if settings.DEBUG_MODE:
                        log_memory_usage()
                    
                    # Wait briefly before next keyword
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing keyword '{keyword}': {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    results["failed_searches"] += 1
                    results["details"][keyword] = {
                        "success": False,
                        "error": str(e)
                    }
            
            # Close browser between batches to free memory
            self.browser.close()
            
            # Force garbage collection
            gc.collect()
            
            # Wait before starting next batch
            if i + batch_size < len(keywords):
                logger.info("Waiting briefly before starting next batch...")
                time.sleep(5)
        
        logger.info(f"Completed processing {len(keywords)} keywords")
        logger.info(f"Success rate: {results['successful_searches']}/{results['total_keywords']} "
                   f"({results['successful_searches']/results['total_keywords']*100:.1f}%)")
        
        return results
        
    except Exception as e:
        logger.error(f"Error running bot with multiple keywords: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return results
        
    finally:
        # Ensure browser is closed
        try:
            self.browser.close()
        except:
            pass

def fetch_mode(args):
    """Run the bot in fetch mode (search for posts and generate review files)"""
    logger.info("Running in FETCH mode")

    # Get all keywords based on language/custom input
    keywords = []
    if args.keywords:
        # Custom keywords provided via command line
        keywords = [k.strip() for k in args.keywords.split(',')]
        logger.info(f"Using {len(keywords)} custom keywords")
    else:
        # Get keywords based on language
        keywords = get_keywords(args.language)
        logger.info(f"Using {len(keywords)} keywords for language: {args.language}")
    
    # Apply limit if specified
    if args.limit and len(keywords) > args.limit:
        keywords = keywords[:args.limit]
        logger.info(f"Limited to first {args.limit} keywords")
    
    # Create and run the bot
    bot = LinkedInRecruitingBot()
    
    # Add the optimized run_multiple_keywords method to the bot
    bot.run_multiple_keywords = run_multiple_keywords.__get__(bot, LinkedInRecruitingBot)
    
    try:
        # Use the memory-optimized method to run with multiple keywords
        result = bot.run_multiple_keywords(
            keywords=keywords,
            language=args.language,
            batch_size=args.batch_size
        )
        
        # Get the number of posts found
        posts_found = result.get('total_posts_found', 0)
        
        # Save statistics
        csv_handler = CSVHandler()
        csv_handler.save_daily_stats(
            keyword=",".join(keywords[:3]) + ("..." if len(keywords) > 3 else ""),
            language=args.language,
            posts_found=posts_found,
            comments_posted=0,
            connections_sent=0
        )
        
        # Generate review file only if new posts were found
        if posts_found > 0:
            # Collect the list of post IDs found in this run from the result details
            new_post_ids = []
            for keyword, details in result.get('details', {}).items():
                if details.get('success', False) and details.get('posts_found', 0) > 0:
                    # We don't have direct access to post IDs here, so we'll generate the review file
                    # for all pending posts instead
                    pass
            
            # Generate review file for all pending posts
            review_file = export_comments_to_review(csv_handler.csv_path)
            if review_file:
                logger.info(f"Generated review file: {review_file}")
                try:
                    # Open the file with default text editor on most systems
                    if sys.platform == 'win32':
                        os.startfile(review_file)
                    elif sys.platform == 'darwin':  # macOS
                        os.system(f'open "{review_file}"')
                    else:  # Linux
                        os.system(f'xdg-open "{review_file}"')
                    logger.info("Review file opened for manual editing")
                except Exception as e:
                    logger.warning(f"Could not automatically open the review file: {e}")
        else:
            logger.info("No new posts found, skipping review file generation")
            
        return True
    
    except Exception as e:
        logger.error(f"Error in fetch mode: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def export_comments_to_review(csv_path, new_post_ids=None):
    """
    Export comments from CSV to a text file for review

    Args:
    csv_path (str): Path to the CSV file
    new_post_ids (list, optional): List of post IDs to include. If None, include all pending posts.

    Returns:
    str: Path to the created text file, or None if no pending comments
    """
    try:
        import pandas as pd
        from config.settings import APPEND_FRIBL_LINK, FRIBL_LINK_EN, FRIBL_LINK_FR, FRIBL_LINK_ES

        # Create review directory if it doesn't exist
        os.makedirs(settings.REVIEW_DIR, exist_ok=True)

        # Load CSV file
        df = pd.read_csv(csv_path)

        # Filter only pending comments
        pending_df = df[df['comment_status'] == 'pending'].copy()  # Create an explicit copy

        # If new_post_ids is provided, only include those posts
        if new_post_ids and len(new_post_ids) > 0:
            # Convert all post_ids to strings for comparison
            pending_df['post_id'] = pending_df['post_id'].astype(str)
            new_post_ids = [str(pid) for pid in new_post_ids]
            
            # Filter to only include posts with IDs in the new_post_ids list
            pending_df = pending_df[pending_df['post_id'].isin(new_post_ids)]
            logger.info(f"Filtered to {len(pending_df)} new posts for review file")

        # Check if dataframe is empty
        if pending_df.empty:
            logger.info("No pending comments to review")
            return None

        # Create output filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(settings.REVIEW_DIR, f"comments_review_{timestamp}.txt")

        # Write to text file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("LinkedIn Recruiting Bot - Comments for Review\n")
            f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 80 + "\n\n")

            f.write("INSTRUCTIONS:\n")
            f.write("1. Review the comments below\n")
            f.write("2. Edit or delete comments as needed\n")
            f.write("3. Move this file to the 'to_send' folder when ready\n")
            f.write("4. Run the bot with --send_comments flag to post these comments\n\n")

            f.write("=" * 80 + "\n\n")

            # Write individual entries for pending comments only
            for i, row in pending_df.iterrows():
                f.write(f"Entry #{i+1}\n")
                f.write(f"post_id: {row.get('post_id')}\n")  # Include post_id for reference
                f.write(f"Lead name: {row.get('author_name', 'Unknown')}\n")
                f.write(f"Post URL: {row.get('post_url', 'Unknown')}\n")
                f.write(f"Post date: {row.get('post_date', 'Unknown')}\n")
                f.write(f"Language: {row.get('language', 'Unknown')}\n")

                # Check if the post has useful content
                post_content = str(row.get('post_content', '')).strip()
                if post_content:
                    f.write("\nPOST CONTENT:\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"{post_content}\n")
                    f.write("-" * 40 + "\n")
                else:
                    f.write("\nPOST CONTENT: [Empty or not available]\n")

                # Get the comment from the row
                comment_text = row.get('comment', 'No comment generated')

                # Show the final comment section (with or without Fribl link)
                f.write("\nFINAL COMMENT (edit as needed):\n")
                f.write("-" * 40 + "\n")

                if APPEND_FRIBL_LINK:
                    # Get language from the row
                    language = row.get('language', 'en').lower()

                    # Select the appropriate link based on language
                    if language == "fr":
                        fribl_link = FRIBL_LINK_FR
                    elif language == "es":
                        fribl_link = FRIBL_LINK_ES
                    else:  # Default to English
                        fribl_link = FRIBL_LINK_EN

                    # Show the comment that will actually be posted
                    full_comment = f"{comment_text} {fribl_link}"
                    f.write(f"{full_comment}\n")
                else:
                    f.write(f"{comment_text}\n")

                f.write("-" * 40 + "\n")

                # Add verification info
                verification = row.get('verification', 'Unknown')
                f.write(f"Comment Type: {verification}\n")

                f.write("\n" + "=" * 80 + "\n\n")

            logger.info(f"Successfully exported comments for review to: {output_file}")
            return output_file

    except Exception as e:
        logger.error(f"Error exporting comments for review: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def load_comments_from_file(file_path):
    """
    Load comments from a review file
    
    Args:
        file_path (str): Path to the review file
        
    Returns:
        list: List of comment dictionaries
    """
    try:
        comments = []
        current_comment = None
        comment_text = ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Start of a new entry
                if line.startswith("Entry #"):
                    # Save previous comment if exists
                    if current_comment and comment_text:
                        current_comment['comment'] = comment_text.strip()
                        comments.append(current_comment)
                    
                    # Start new comment
                    current_comment = {}
                    comment_text = ""
                
                # Parse post_id
                elif line.startswith("post_id:"):
                    if current_comment is not None:
                        current_comment['post_id'] = line.replace("post_id:", "").strip()
                
                # Parse post URL
                elif line.startswith("Post URL:"):
                    if current_comment is not None:
                        current_comment['post_url'] = line.replace("Post URL:", "").strip()
                
                # Parse language
                elif line.startswith("Language:"):
                    if current_comment is not None:
                        current_comment['language'] = line.replace("Language:", "").strip()
                
                # Start of FINAL comment section (changed from COMMENT to FINAL COMMENT)
                elif line == "FINAL COMMENT (edit as needed):":
                    # Skip the separator line
                    i += 2
                    
                    # Collect comment text until the separator
                    while i < len(lines) and not lines[i].strip().startswith("-" * 10):
                        comment_text += lines[i]
                        i += 1
                    
                    # Skip to the next line after the separator
                    continue
                
                # For backward compatibility with older files that might not have FINAL COMMENT
                elif line == "COMMENT (edit as needed):" and not current_comment.get('comment'):
                    # Skip the separator line
                    i += 2
                    
                    # Collect comment text until the separator
                    while i < len(lines) and not lines[i].strip().startswith("-" * 10):
                        comment_text += lines[i]
                        i += 1
                    
                    # Skip to the next line after the separator
                    continue
                
                i += 1
            
            # Save the last comment
            if current_comment and comment_text:
                current_comment['comment'] = comment_text.strip()
                comments.append(current_comment)
        
        logger.info(f"Loaded {len(comments)} comments from file: {file_path}")
        
        # Post-process comments to remove Fribl link if it's going to be added automatically
        from config.settings import (
                                            APPEND_FRIBL_LINK, 
                                            FRIBL_LINK_EN, 
                                            FRIBL_LINK_FR, 
                                            FRIBL_LINK_ES,
                                            FRIBL_BASE_LINK
                                        )

        if APPEND_FRIBL_LINK:
            for comment in comments:
                if 'comment' in comment and 'language' in comment:
                    language = comment['language'].lower()
                    
                    # Check for all possible Fribl links based on language
                    if language == "fr" and comment['comment'].endswith(FRIBL_LINK_FR):
                        comment['comment'] = comment['comment'][:-len(FRIBL_LINK_FR)].strip()
                    elif language == "es" and comment['comment'].endswith(FRIBL_LINK_ES):
                        comment['comment'] = comment['comment'][:-len(FRIBL_LINK_ES)].strip()
                    elif comment['comment'].endswith(FRIBL_LINK_EN):
                        comment['comment'] = comment['comment'][:-len(FRIBL_LINK_EN)].strip()
                    
                    # Also check for just the base link without the "It's Free" message
                    elif FRIBL_BASE_LINK in comment['comment']:
                        idx = comment['comment'].find(FRIBL_BASE_LINK)
                        # Only remove if it's at the end or part of a phrase at the end
                        if idx > len(comment['comment']) - len(FRIBL_BASE_LINK) - 30:
                            # Try to preserve the comment part and remove just the link part
                            comment['comment'] = comment['comment'][:idx].strip()
        
        return comments
        
    except Exception as e:
        logger.error(f"Error loading comments from file: {e}")
        return []

def move_file_to_connect(file_path):
    """
    Move a file to the to_connect directory
    
    Args:
        file_path (str): Path to the file to move
        
    Returns:
        str: Path to the moved file
    """
    try:
        filename = os.path.basename(file_path)
        connect_path = os.path.join(settings.TO_CONNECT_DIR, filename)
        
        # If the file already exists in the to_connect dir, add a timestamp
        if os.path.exists(connect_path):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            connect_path = os.path.join(settings.TO_CONNECT_DIR, f"{name}_{timestamp}{ext}")
        
        # Move the file
        os.rename(file_path, connect_path)
        
        logger.info(f"Moved file to to_connect folder: {connect_path}")
        return connect_path
        
    except Exception as e:
        logger.error(f"Error moving file to to_connect folder: {e}")
        return None

def move_file_to_archive(file_path):
    """
    Move a file to the archive directory
    
    Args:
        file_path (str): Path to the file to archive
        
    Returns:
        str: Path to the archived file
    """
    try:
        filename = os.path.basename(file_path)
        archive_path = os.path.join(settings.ARCHIVED_DIR, filename)
        
        # If the file already exists in the archive, add a timestamp
        if os.path.exists(archive_path):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            archive_path = os.path.join(settings.ARCHIVED_DIR, f"{name}_{timestamp}{ext}")
        
        # Move the file
        os.rename(file_path, archive_path)
        
        logger.info(f"Moved file to archive: {archive_path}")
        return archive_path
        
    except Exception as e:
        logger.error(f"Error moving file to archive: {e}")
        return None

def split_comments_file(file_path, sent_count):
    """
    Split a comments file after some comments have been sent
    
    Args:
        file_path (str): Path to the comments file
        sent_count (int): Number of comments that have been sent
        
    Returns:
        tuple: (to_connect_file_path, remaining_file_path)
    """
    try:
        # Load comments from file
        comments = load_comments_from_file(file_path)
        
        if not comments:
            logger.error(f"No comments found in file: {file_path}")
            return None, None
        
        if sent_count <= 0 or sent_count >= len(comments):
            logger.warning(f"Invalid sent count: {sent_count}")
            return None, None
        
        # Split comments into sent and remaining
        sent_comments = comments[:sent_count]
        remaining_comments = comments[sent_count:]
        
        # Create filenames for the split files
        filename = os.path.basename(file_path)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        to_connect_file = os.path.join(settings.TO_CONNECT_DIR, f"sent_{timestamp}_{filename}")
        remaining_file = os.path.join(settings.TO_SEND_DIR, f"remaining_{timestamp}_{filename}")
        
        # Write sent comments to to_connect file
        with open(to_connect_file, 'w', encoding='utf-8') as f:
            f.write("LinkedIn Recruiting Bot - Sent Comments\n")
            f.write(f"Original file: {filename}\n")
            f.write(f"Sent on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 80 + "\n\n")
            
            for i, comment in enumerate(sent_comments):
                f.write(f"Entry #{i+1}\n")
                for key, value in comment.items():
                    if key != 'comment':
                        f.write(f"{key}: {value}\n")
                
                f.write("\nCOMMENT:\n")
                f.write("-" * 40 + "\n")
                f.write(f"{comment.get('comment', '')}\n")
                f.write("-" * 40 + "\n")
                f.write(f"STATUS: SENT\n\n")
                f.write("=" * 80 + "\n\n")
        
        # Write remaining comments to remaining file
        with open(remaining_file, 'w', encoding='utf-8') as f:
            f.write("LinkedIn Recruiting Bot - Remaining Comments\n")
            f.write(f"Original file: {filename}\n")
            f.write(f"Split on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 80 + "\n\n")
            
            f.write("INSTRUCTIONS:\n")
            f.write("1. These comments were not sent due to daily limit\n")
            f.write("2. They will be processed next time you run with --send_comments flag\n\n")
            
            f.write("=" * 80 + "\n\n")
            
            for i, comment in enumerate(remaining_comments):
                f.write(f"Entry #{i+1}\n")
                for key, value in comment.items():
                    if key != 'comment':
                        f.write(f"{key}: {value}\n")
                
                f.write("\nCOMMENT:\n")
                f.write("-" * 40 + "\n")
                f.write(f"{comment.get('comment', '')}\n")
                f.write("-" * 40 + "\n")
                f.write("\n" + "=" * 80 + "\n\n")
        
        # Delete the original file
        os.remove(file_path)
        
        logger.info(f"Split comments file into sent ({sent_count}) and remaining ({len(remaining_comments)})")
        return to_connect_file, remaining_file
        
    except Exception as e:
        logger.error(f"Error splitting comments file: {e}")
        return None, None

def post_comments(bot, comments):
    """
    Post comments from a list
    
    Args:
        bot (LinkedInRecruitingBot): Bot instance
        comments (list): List of comment dictionaries
        
    Returns:
        int: Number of comments successfully posted
    """
    comments_posted = 0
    csv_handler = CSVHandler()
    
    for comment_data in comments:
        post_url = comment_data.get('post_url')
        post_id = comment_data.get('post_id')
        comment = comment_data.get('comment')
        language = comment_data.get('language', 'en')
        
        if not post_url or not comment or not post_id:
            logger.warning(f"Missing required data for comment on post {post_id}")
            continue
        
        # Fix generated URLs by trying to create a valid LinkedIn URL
        if "generated_" in post_url:
            logger.warning(f"Found generated URL: {post_url}, attempting to fix it")
            # Try to create a valid URL from the post_id
            if "urn:li:activity:" in post_id:
                post_url = f"https://www.linkedin.com/feed/update/{post_id}"
                logger.info(f"Fixed URL to: {post_url}")
            else:
                # If we can't fix the URL, skip this post
                logger.error(f"Cannot fix generated URL for post {post_id}")
                continue
        
        # Navigate to post
        if not bot.browser.navigate_to(post_url):
            logger.error(f"Failed to navigate to post URL: {post_url}")
            continue
        
        # Post comment
        if bot.post_comment(post_id, comment, language):
            comments_posted += 1
            
            # Update comment status in CSV
            csv_handler.update_comment_status(post_id, "posted")
            
            # Add some delay between comments to avoid rate limiting
            bot.browser.human_wait(5, 10)
        else:
            logger.error(f"Failed to post comment on post {post_id}")
    
    return comments_posted

def send_comments_mode(args):
    """Run the bot in send_comments mode (post comments from ready-to-send files)"""
    logger.info("Running in SEND_COMMENTS mode")
    
    # Check if there are files in the to_send directory
    to_send_files = [f for f in os.listdir(settings.TO_SEND_DIR) if f.endswith('.txt')]
    
    if not to_send_files:
        logger.info("No files found in the to_send directory")
        return True
    
    logger.info(f"Found {len(to_send_files)} files to process")
    
    # Create and run the bot
    bot = LinkedInRecruitingBot()
    
    try:
        # Initialize browser
        if not bot.browser.initialize():
            logger.error("Failed to initialize browser. Aborting.")
            return False
        
        # Login to LinkedIn
        if not bot.auth.login():
            logger.error("Failed to login to LinkedIn. Aborting.")
            return False
        
        # Initialize counters
        comments_posted = 0
        daily_comment_limit = settings.DAILY_COMMENT_LIMIT
        
        # Process each file in the to_send directory
        for filename in to_send_files:
            file_path = os.path.join(settings.TO_SEND_DIR, filename)
            logger.info(f"Processing file: {filename}")
            
            # Load comments from file
            comments = load_comments_from_file(file_path)
            
            if not comments:
                logger.warning(f"No valid comments found in file: {filename}")
                continue
            
            # Check if we would exceed the daily comment limit
            if comments_posted + len(comments) > daily_comment_limit:
                # Calculate how many comments we can still send
                remaining_limit = daily_comment_limit - comments_posted
                
                if remaining_limit <= 0:
                    logger.warning("Daily comment limit reached. Skipping remaining files.")
                    break
                
                logger.warning(f"File contains more comments than remaining daily limit ({remaining_limit}). Will split the file.")
                
                # Post comments up to the limit
                sent_count = post_comments(bot, comments[:remaining_limit])
                comments_posted += sent_count
                
                # Split the file if we sent any comments
                if sent_count == len(comments):
                    move_file_to_archive(file_path)  
                else:
                    # Split the file
                    split_comments_file(file_path, sent_count)
                
                # We've reached the limit, stop processing files
                logger.info(f"Reached daily comment limit ({daily_comment_limit}). Posted {comments_posted} comments.")
                break
            
            # Post all comments in the file
            sent_count = post_comments(bot, comments)
            comments_posted += sent_count
            
            # If all comments were successfully posted, move the file to archive
            if sent_count == len(comments):
                move_file_to_archive(file_path)
            else:
                # Split the file
                split_comments_file(file_path, sent_count)
            
            # Check if we've reached the daily limit
            if comments_posted >= daily_comment_limit:
                logger.info(f"Reached daily comment limit ({daily_comment_limit}). Posted {comments_posted} comments.")
                break
        
        # Save statistics
        csv_handler = CSVHandler()
        csv_handler.save_daily_stats(
            keyword="send_comments_mode",
            language="all",
            posts_found=0,
            comments_posted=comments_posted,
            connections_sent=0  # Always 0 since we're not sending connections
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Error in send comments mode: {e}")
        return False
    
    finally:
        # Close browser
        bot.browser.close()

def comment_mode(args):
    """Run the bot in comment mode"""
    logger.info("Running in COMMENT mode")
    
    # Get pending comments to post
    csv_handler = CSVHandler()
    pending_posts = csv_handler.get_pending_comments(args.limit)
    
    if not pending_posts:
        logger.info("No pending comments to post")
        return True
    
    logger.info(f"Found {len(pending_posts)} pending comments to post")
    
    # Create and run the bot
    bot = LinkedInRecruitingBot()
    
    try:
        # Initialize browser
        if not bot.browser.initialize():
            logger.error("Failed to initialize browser. Aborting.")
            return False
        
        # Login to LinkedIn
        if not bot.auth.login():
            logger.error("Failed to login to LinkedIn. Aborting.")
            return False
        
        # Post comments
        comments_posted = 0
        for post in pending_posts:
            post_url = post.get('post_url')
            post_id = post.get('post_id')
            comment = post.get('comment')
            language = post.get('language', 'en')
            
            if not post_url or not comment:
                logger.warning(f"Missing post URL or comment for post {post_id}")
                continue
            
            # Navigate to post
            if not bot.browser.navigate_to(post_url):
                logger.error(f"Failed to navigate to post URL: {post_url}")
                continue
            
            # Post comment
            if bot.post_comment(post_id, comment, language):
                comments_posted += 1
                
                # Update comment status in CSV
                csv_handler.update_comment_status(post_id, "posted")
        
        logger.info(f"Posted {comments_posted} comments")
        
        # Save statistics
        csv_handler.save_daily_stats(
            keyword="comment_mode",
            language=args.language,
            posts_found=0,
            comments_posted=comments_posted,
            connections_sent=0
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Error in comment mode: {e}")
        return False
    
    finally:
        # Close browser
        bot.browser.close()

def connect_mode(args):
    """Run the bot in connect mode"""
    logger.info("Running in CONNECT mode")
    
    # Create connection manager
    bot = LinkedInRecruitingBot()
    
    try:
        # Initialize browser
        if not bot.browser.initialize():
            logger.error("Failed to initialize browser. Aborting.")
            return False
        
        # Login to LinkedIn
        if not bot.auth.login():
            logger.error("Failed to login to LinkedIn. Aborting.")
            return False
        
        # Check weekly connection limit
        csv_handler = CSVHandler()
        weekly_count = csv_handler.get_weekly_connection_count()
        weekly_limit = settings.CONNECTION_WEEKLY_LIMIT
        
        if weekly_count >= weekly_limit:
            logger.warning(f"Weekly connection limit reached ({weekly_count}/{weekly_limit}). Skipping connections.")
            return True
        
        available_connections = weekly_limit - weekly_count
        connections_to_send = min(available_connections, args.limit)
        
        logger.info(f"Can send {connections_to_send} more connections this week ({weekly_count}/{weekly_limit} used)")
        
        if connections_to_send <= 0:
            return True
        
        # Get posts with comments but no connection request
        posts = []
        existing_posts, _ = csv_handler.load_history()
        
        for post in existing_posts:
            # Only consider posts with successful comments and no connection request yet
            if (post.get('comment_status') == 'posted' and 
                post.get('connection_requested', '').lower() != 'true'):
                posts.append(post)
        
        logger.info(f"Found {len(posts)} potential posts for connections")
        
        # Send connection requests
        connections_sent = 0
        for post in posts[:connections_to_send]:
            author_name = post.get('author_name')
            author_profile_url = post.get('author_profile_url')
            post_id = post.get('post_id')
            
            if not author_profile_url:
                logger.warning(f"No profile URL for author {author_name}")
                continue
            
            # Send connection request
            if bot.connection_manager.send_connection_request(
                profile_url=author_profile_url,
                keyword=post.get('keyword', 'recruiting')
            ):
                connections_sent += 1
                
                # Update connection status in CSV
                csv_handler.update_connection_status(post_id, "sent")
                
                # Don't send too many at once (avoid LinkedIn limits)
                if connections_sent >= connections_to_send:
                    break
        
        logger.info(f"Sent {connections_sent} connection requests")
        
        # Save statistics
        csv_handler.save_daily_stats(
            keyword="connect_mode",
            language=args.language,
            posts_found=0,
            comments_posted=0,
            connections_sent=connections_sent
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Error in connect mode: {e}")
        return False
    
    finally:
        # Close browser
        bot.browser.close()

def main():
    """Main entry point"""
    logger.info("Starting LinkedIn Recruiting Bot")
    
    # Parse arguments
    args = parse_arguments()
    
    # Set debug mode from arguments
    settings.DEBUG_MODE = args.debug
    settings.HEADLESS = args.headless
    
    # Import memory monitoring utility
    try:
        from utils.memory_monitor import log_memory_usage, clean_memory
    except ImportError:
        # Create the memory monitor module if it doesn't exist
        logger.info("Creating memory monitoring utility")
        os.makedirs("utils", exist_ok=True)
        with open("utils/memory_monitor.py", "w") as f:
            f.write("""\"\"\"

import os
import gc
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Try to import psutil, but provide fallbacks if it's not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger = setup_logger(__name__)
    logger.warning("psutil package not available. Memory monitoring will be limited.")
    logger.warning("Install psutil with: pip install psutil")

def get_process_memory():
    \"\"\"
    Get current memory usage of the process in MB
    
    Returns:
        float: Memory usage in MB
    \"\"\"
    if not PSUTIL_AVAILABLE:
        # If psutil is not available, trigger garbage collection and return a placeholder
        gc.collect()
        return 0.0  # Just return 0 since we can't measure
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # Return in MB
    return memory_info.rss / (1024 * 1024)

def log_memory_usage():
    \"\"\"
    Log current memory usage
    \"\"\"
    memory_mb = get_process_memory()
    logger.info(f"Current memory usage: {memory_mb:.2f} MB")

def clean_memory():
    \"\"\"
    Attempt to free up memory
    \"\"\"
    before = get_process_memory()
    
    # Force garbage collection
    gc.collect()
    
    # Get memory after cleanup
    after = get_process_memory()
    
    logger.info(f"Memory cleanup: {before:.2f} MB -> {after:.2f} MB (freed {before - after:.2f} MB)")
    
    return before - after

def memory_warning_check(threshold_mb=1000):
    \"\"\"
    Check if memory usage exceeds threshold
    
    Args:
        threshold_mb (int): Memory threshold in MB
        
    Returns:
        bool: True if memory usage exceeds threshold
    \"\"\"
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
""")
        logger.info("Created memory monitoring utility")
        from utils.memory_monitor import log_memory_usage, clean_memory

    csv_handler = CSVHandler()
    duplicates_removed = csv_handler.deduplicate_existing_posts()
    if duplicates_removed > 0:
        logger.info(f"Cleaned up database: removed {duplicates_removed} duplicate posts")

    # Display settings
    logger.info(f"Running with settings:")
    if args.fetch:
        logger.info("  Mode: FETCH")
    elif args.send_comments:
        logger.info("  Mode: SEND_COMMENTS")
    elif args.fetch_and_send:
        logger.info("  Mode: FETCH AND SEND")
    elif args.stats:
        logger.info("  Mode: STATS")
    else:
        logger.info("  Mode: None specified (use --fetch, --send_comments, --fetch-and-send, or --stats)")
    
    logger.info(f"  Limit: {args.limit}")
    logger.info(f"  Language: {args.language}")
    if args.batch_size:
        logger.info(f"  Batch size: {args.batch_size}")
    logger.info(f"  Debug mode: {settings.DEBUG_MODE}")
    logger.info(f"  Headless mode: {settings.HEADLESS}")
    
    # Log initial memory usage
    log_memory_usage()
    
    # Check dependencies and credentials
    if not check_dependencies() or not check_credentials():
        sys.exit(1)
    
    # Handle stats mode separately
    if args.stats:
        stats_file = generate_stats_report()
        if stats_file:
            # Open the file with default text editor
            try:
                if sys.platform == 'win32':
                    os.startfile(stats_file)
                elif sys.platform == 'darwin':  # macOS
                    os.system(f'open "{stats_file}"')
                else:  # Linux
                    os.system(f'xdg-open "{stats_file}"')
                logger.info("Stats report opened for review")
                sys.exit(0)
            except Exception as e:
                logger.warning(f"Could not automatically open the stats file: {e}")
                sys.exit(1)
        else:
            logger.error("Failed to generate stats report")
            sys.exit(1)
    
    # Run in the specified mode
    success = False
    
    if not (args.fetch or args.send_comments or args.fetch_and_send):
        logger.error("No mode specified. Use --fetch, --send_comments, --fetch-and-send, or --stats")
        sys.exit(1)
    
    if args.fetch or args.fetch_and_send:
        fetch_success = fetch_mode(args)
        success = fetch_success
        if not fetch_success:
            logger.error("Fetch mode failed")
            if not args.fetch_and_send:
                sys.exit(1)
    
    if args.send_comments or args.fetch_and_send:
        send_success = send_comments_mode(args)
        success = success or send_success
        if not send_success:
            logger.error("Send comments mode failed")
            sys.exit(1)
    
    # Final memory cleanup
    clean_memory()
    
    if success:
        logger.info("Bot finished successfully")
        sys.exit(0)
    else:
        logger.error("Bot failed")
        sys.exit(1)

if __name__ == "__main__":
    print("LinkedIn Recruiting Bot is starting...")
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot terminated by user")
        # Force garbage collection before exit
        gc.collect()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)