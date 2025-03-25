"""
CSV storage handler for LinkedIn Recruiting Bot
"""
import os
import csv
import datetime
import pandas as pd
import hashlib
from utils.logger import setup_logger
from config import settings  # Ajoutez cette ligne

logger = setup_logger(__name__)

class CSVHandler:
    """Handle CSV storage for LinkedIn posts and connections"""
    
    def __init__(self, csv_path=None):
        """
        Initialize CSV handler
        
        Args:
            csv_path (str, optional): Path to CSV file. Defaults to None.
        """
        self.csv_path = csv_path or settings.CSV_PATH
        self.connection_csv_path = settings.CONNECTIONS_CSV_PATH
        self.stats_csv_path = settings.STATS_CSV_PATH
        
        # Ensure CSV files exist with headers
        self._ensure_posts_csv_exists()
        self._ensure_connections_csv_exists()
        self._ensure_stats_csv_exists()
    
    def _ensure_posts_csv_exists(self):
        """Ensure posts CSV file exists with proper headers"""
        if not os.path.exists(self.csv_path):
            logger.info(f"Creating new posts CSV file: {self.csv_path}")
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "post_id", 
                    "post_date", 
                    "post_date_text", 
                    "post_content", 
                    "post_url", 
                    "author_name",
                    "author_profile_url",
                    "language",
                    "comment", 
                    "verification",
                    "commented_at",
                    "comment_status",
                    "connection_requested",
                    "connection_status"
                ])
    
    def _ensure_connections_csv_exists(self):
        """Ensure connections CSV file exists with proper headers"""
        if not os.path.exists(self.connection_csv_path):
            logger.info(f"Creating new connections CSV file: {self.connection_csv_path}")
            os.makedirs(os.path.dirname(self.connection_csv_path), exist_ok=True)
            
            with open(self.connection_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "profile_id",
                    "profile_url",
                    "name",
                    "request_date",
                    "status",
                    "notes",
                    "keyword"
                ])
    
    def _ensure_stats_csv_exists(self):
        """Ensure stats CSV file exists with proper headers"""
        if not os.path.exists(self.stats_csv_path):
            logger.info(f"Creating new stats CSV file: {self.stats_csv_path}")
            os.makedirs(os.path.dirname(self.stats_csv_path), exist_ok=True)
            
            with open(self.stats_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "date",
                    "keyword",
                    "language",
                    "posts_found",
                    "comments_posted",
                    "connections_sent",
                    "cumulative_comments",
                    "cumulative_connections"
                ])
    
    def load_history(self):
        """
        Load post history from CSV and create identifiers for duplicate detection
        
        Returns:
            tuple: (list of post dicts, dict of post identifiers)
        """
        try:
            if not os.path.exists(self.csv_path):
                logger.info("No existing CSV file found")
                return [], {}
            
            # Read CSV into DataFrame
            df = pd.read_csv(self.csv_path)
            
            # Convert DataFrame to list of dicts
            posts = df.to_dict('records')
            logger.info(f"Loaded {len(posts)} existing posts from CSV")
            
            # Create identifiers for duplicate detection
            post_identifiers = {}
            
            for post in posts:
                # Convert post_id to string to ensure consistent comparison
                post_id = str(post.get('post_id', ''))
                if post_id:
                    post_identifiers[post_id] = True
                    
                # Add URL identifier for more thorough duplicate detection
                post_url = post.get('post_url', '')
                if post_url and '/feed/update/' in post_url:
                    url_id = post_url.split('/feed/update/')[-1].split('?')[0].strip()
                    post_identifiers[url_id] = True
                    
                # Add content hash for even more thorough duplicate detection
                post_content = post.get('post_content', '')
                if post_content:
                    for sample_size in [50, 100, 150]:
                        if len(post_content) >= sample_size:
                            content_preview = post_content[:sample_size].lower()
                            content_hash = hashlib.md5(content_preview.encode()).hexdigest()
                            post_identifiers[content_hash] = True
            
            logger.info(f"Created {len(post_identifiers)} unique identifiers for duplicate detection")
            return posts, post_identifiers
        
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return [], {}
    
    def load_connection_history(self):
        """
        Load existing connection history
        
        Returns:
            tuple: (List of existing connections, Dict of profile identifiers)
        """
        existing_connections = []
        profile_identifiers = {}
        
        try:
            if os.path.exists(self.connection_csv_path):
                with open(self.connection_csv_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        existing_connections.append(row)
                        
                        # Store profile identifiers to avoid duplicates
                        profile_id = row.get('profile_id', '')
                        if profile_id:
                            profile_identifiers[profile_id] = True
                        
                        profile_url = row.get('profile_url', '')
                        if profile_url:
                            profile_identifiers[profile_url] = True
                
                logger.info(f"Loaded {len(existing_connections)} existing connections from CSV")
            else:
                logger.info("No existing connections CSV found, starting with empty history")
        except Exception as e:
            logger.error(f"Error loading connection history: {e}")
        
        return existing_connections, profile_identifiers
    


    def save_posts(self, posts):
        """
        Save posts to CSV
        
        Args:
            posts (list): List of post dictionaries
            
        Returns:
            int: Number of posts saved
        """
        saved_count = 0
        
        try:
            # Load existing posts to append to
            existing_posts, _ = self.load_history()
            
            # Débogage - Afficher les champs du premier post
            if posts and len(posts) > 0:
                logger.info(f"Fields in first post: {list(posts[0].keys())}")
            
            # Get the fieldnames from the first post or use default headers
            fieldnames = None
            if posts and len(posts) > 0:
                fieldnames = list(posts[0].keys())
                logger.info(f"Using fieldnames from first post: {fieldnames}")
            elif existing_posts and len(existing_posts) > 0:
                fieldnames = list(existing_posts[0].keys())
                logger.info(f"Using fieldnames from existing posts: {fieldnames}")
            else:
                fieldnames = [
                    "post_id", 
                    "post_date", 
                    "post_date_text", 
                    "post_content", 
                    "post_url", 
                    "author_name",
                    "author_profile_url",
                    "language",
                    "comment", 
                    "verification",
                    "commented_at",
                    "comment_status",
                    "connection_requested",
                    "connection_status"
                ]
                logger.info(f"Using default fieldnames: {fieldnames}")
            
            # Ensure all posts have all fields
            for post in posts:

                for field in ['post_content', 'author_name', 'comment']:
                        if field in post and post[field] is not None and not isinstance(post[field], str):
                            post[field] = str(post[field])

                missing_fields = [field for field in fieldnames if field not in post]
                if missing_fields:
                    logger.info(f"Adding missing fields to post: {missing_fields}")
                
                for field in fieldnames:
                    if field not in post:
                        post[field] = ""
                        
                # Ensure newly added fields are included
                if "language" not in post:
                    post["language"] = ""
                if "author_profile_url" not in post:
                    post["author_profile_url"] = ""
                if "comment_status" not in post:
                    post["comment_status"] = "pending"
                if "connection_requested" not in post:
                    post["connection_requested"] = "false"
                if "connection_status" not in post:
                    post["connection_status"] = ""
            
            # Write all posts to CSV
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write existing posts first
                for post in existing_posts:
                    # Assurez-vous que tous les posts existants ont tous les champs
                    for field in fieldnames:
                        if field not in post:
                            post[field] = ""
                    writer.writerow(post)
                
                # Write new posts
                for post in posts:
                    # Vérification finale
                    for field in fieldnames:
                        if field not in post:
                            logger.warning(f"Field {field} still missing from post despite adding it earlier")
                            post[field] = ""
                    writer.writerow(post)
                    saved_count += 1
            
            logger.info(f"Saved {saved_count} posts to CSV")
            
        except Exception as e:
            logger.error(f"Error saving posts: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        return saved_count
    
    def save_connection(self, profile_id, profile_url, name, status="sent", notes="", keyword=""):
        """
        Save a connection request to CSV
        
        Args:
            profile_id (str): LinkedIn profile ID
            profile_url (str): LinkedIn profile URL
            name (str): Person's name
            status (str, optional): Connection status. Defaults to "sent".
            notes (str, optional): Additional notes. Defaults to "".
            keyword (str, optional): Keyword used to find this connection. Defaults to "".
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            with open(self.connection_csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    profile_id,
                    profile_url,
                    name,
                    datetime.datetime.now().strftime("%Y-%m-%d"),
                    status,
                    notes,
                    keyword
                ])
            
            logger.info(f"Saved connection request to {name} ({profile_url})")
            return True
            
        except Exception as e:
            logger.error(f"Error saving connection: {e}")
            return False
    
    def get_weekly_connection_count(self):
        """
        Get the number of connection requests sent in the current week
        
        Returns:
            int: Number of connection requests sent this week
        """
        count = 0
        today = datetime.datetime.now().date()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        
        try:
            if os.path.exists(self.connection_csv_path):
                with open(self.connection_csv_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            request_date = datetime.datetime.strptime(row.get('request_date', ''), "%Y-%m-%d").date()
                            if request_date >= start_of_week:
                                count += 1
                        except ValueError:
                            continue
        except Exception as e:
            logger.error(f"Error counting weekly connections: {e}")
        
        return count
    
    def update_comment_status(self, post_id, status="posted"):
        """
        Update the status of a comment
        
        Args:
            post_id (str): Post ID
            status (str, optional): Comment status. Defaults to "posted".
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            # Load existing posts
            existing_posts, _ = self.load_history()
            updated = False
            
            for post in existing_posts:
                if post.get('post_id') == post_id:
                    post['comment_status'] = status
                    post['commented_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    updated = True
            
            if updated:
                # Save all posts back to CSV
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=existing_posts[0].keys())
                    writer.writeheader()
                    for post in existing_posts:
                        writer.writerow(post)
                
                logger.info(f"Updated comment status for post {post_id} to {status}")
                return True
            else:
                logger.warning(f"Post {post_id} not found in CSV")
                return False
                
        except Exception as e:
            logger.error(f"Error updating comment status: {e}")
            return False
    
    def update_connection_status(self, post_id, status="sent"):
        """
        Update the connection status for a post
        
        Args:
            post_id (str): Post ID
            status (str, optional): Connection status. Defaults to "sent".
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
        # Check if status is valid
            valid_statuses = ['pending', 'posted', 'failed', 'skipped_invalid_url']
            
            if status not in valid_statuses:
                logger.warning(f"Invalid status: {status}. Must be one of {valid_statuses}")
                return False


            # Load existing posts
            existing_posts, _ = self.load_history()
            updated = False
            
            for post in existing_posts:
                if post.get('post_id') == post_id:
                    post['connection_requested'] = "true"
                    post['connection_status'] = status
                    updated = True
            
            if updated:
                # Save all posts back to CSV
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=existing_posts[0].keys())
                    writer.writeheader()
                    for post in existing_posts:
                        writer.writerow(post)
                
                logger.info(f"Updated connection status for post {post_id} to {status}")
                return True
            else:
                logger.warning(f"Post {post_id} not found in CSV")
                return False
                
        except Exception as e:
            logger.error(f"Error updating connection status: {e}")
            return False
    
    def get_pending_comments(self, limit=None):
        """
        Get pending comments from CSV

        Args:
        limit (int, optional): Maximum number of comments to return. Defaults to None.

        Returns:
        list: List of post dictionaries with pending comments
        """
        try:
            if not os.path.exists(self.csv_path):
                return []

            # Load CSV into DataFrame
            df = pd.read_csv(self.csv_path)

            # Filter only pending comments
            pending_df = df[df['comment_status'] == 'pending']

            # Convert to list of dictionaries
            pending_posts = pending_df.to_dict('records')

            # Apply limit if specified
            if limit and len(pending_posts) > limit:
                pending_posts = pending_posts[:limit]

            logger.info(f"Found {len(pending_posts)} pending comments")
            return pending_posts

        except Exception as e:
            logger.error(f"Error getting pending comments: {e}")
            return []
    
    def save_daily_stats(self, keyword, language, posts_found, comments_posted, connections_sent):
        """
        Save daily statistics
        
        Args:
            keyword (str): Keyword used for search
            language (str): Language used for comments
            posts_found (int): Number of posts found
            comments_posted (int): Number of comments posted
            connections_sent (int): Number of connection requests sent
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Calculate cumulative totals
            total_comments = 0
            total_connections = 0
            
            if os.path.exists(self.stats_csv_path):
                with open(self.stats_csv_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        total_comments = max(total_comments, int(row.get('cumulative_comments', 0)))
                        total_connections = max(total_connections, int(row.get('cumulative_connections', 0)))
            
            # Update with today's counts
            total_comments += comments_posted
            total_connections += connections_sent
            
            # Save the stats
            with open(self.stats_csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.datetime.now().strftime("%Y-%m-%d"),
                    keyword,
                    language,
                    posts_found,
                    comments_posted,
                    connections_sent,
                    total_comments,
                    total_connections
                ])
            
            logger.info(f"Saved daily stats for keyword '{keyword}'")
            return True
            
        except Exception as e:
            logger.error(f"Error saving daily stats: {e}")
            return False
    
    def get_stats_summary(self, days=7):
        """
        Get statistics summary for reporting
        
        Args:
            days (int, optional): Number of days to include. Defaults to 7.
            
        Returns:
            dict: Statistics summary
        """
        summary = {
            'total_posts_found': 0,
            'total_comments_posted': 0,
            'total_connections_sent': 0,
            'all_time_comments': 0,
            'all_time_connections': 0,
            'daily_stats': [],
            'keywords_stats': {},
            'languages_stats': {}
        }
        
        try:
            if os.path.exists(self.stats_csv_path):
                # Calculate date threshold
                today = datetime.datetime.now().date()
                threshold_date = today - datetime.timedelta(days=days)
                
                with open(self.stats_csv_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            row_date = datetime.datetime.strptime(row.get('date', ''), "%Y-%m-%d").date()
                            
                            # Track overall stats
                            summary['all_time_comments'] = int(row.get('cumulative_comments', 0))
                            summary['all_time_connections'] = int(row.get('cumulative_connections', 0))
                            
                            # Track stats within the specified days range
                            if row_date >= threshold_date:
                                # Add to daily stats
                                summary['daily_stats'].append({
                                    'date': row_date.strftime("%Y-%m-%d"),
                                    'posts_found': int(row.get('posts_found', 0)),
                                    'comments_posted': int(row.get('comments_posted', 0)),
                                    'connections_sent': int(row.get('connections_sent', 0))
                                })
                                
                                # Update totals
                                summary['total_posts_found'] += int(row.get('posts_found', 0))
                                summary['total_comments_posted'] += int(row.get('comments_posted', 0))
                                summary['total_connections_sent'] += int(row.get('connections_sent', 0))
                                
                                # Update keyword stats
                                keyword = row.get('keyword', 'unknown')
                                if keyword not in summary['keywords_stats']:
                                    summary['keywords_stats'][keyword] = {
                                        'posts_found': 0,
                                        'comments_posted': 0,
                                        'connections_sent': 0
                                    }
                                summary['keywords_stats'][keyword]['posts_found'] += int(row.get('posts_found', 0))
                                summary['keywords_stats'][keyword]['comments_posted'] += int(row.get('comments_posted', 0))
                                summary['keywords_stats'][keyword]['connections_sent'] += int(row.get('connections_sent', 0))
                                
                                # Update language stats
                                language = row.get('language', 'unknown')
                                if language not in summary['languages_stats']:
                                    summary['languages_stats'][language] = {
                                        'posts_found': 0,
                                        'comments_posted': 0,
                                        'connections_sent': 0
                                    }
                                summary['languages_stats'][language]['posts_found'] += int(row.get('posts_found', 0))
                                summary['languages_stats'][language]['comments_posted'] += int(row.get('comments_posted', 0))
                                summary['languages_stats'][language]['connections_sent'] += int(row.get('connections_sent', 0))
                        except ValueError:
                            continue
        except Exception as e:
            logger.error(f"Error getting stats summary: {e}")
        
        return summary

    def deduplicate_existing_posts(self):
        """
        Clean up the existing CSV file by removing duplicate posts

        Returns:
        int: Number of duplicates removed
        """
        try:
            if not os.path.exists(self.csv_path):
                return 0

            # Load CSV into DataFrame
            df = pd.read_csv(self.csv_path)
            original_count = len(df)

            # First pass: remove exact duplicates
            df = df.drop_duplicates(subset=['post_id'])

            # Second pass: remove content-based duplicates
            content_hashes = {}
            rows_to_keep = []

            for i, row in df.iterrows():
                content = row.get('post_content', '')
                author = row.get('author_name', '')

                if not content or not author:
                    rows_to_keep.append(i)
                    continue

                # Create a content hash based on author and first 100 chars
                content_preview = f"{author.lower()}:{content[:100].lower()}"
                content_hash = hashlib.md5(content_preview.encode()).hexdigest()

                if content_hash not in content_hashes:
                    content_hashes[content_hash] = i
                    rows_to_keep.append(i)

            # Keep only non-duplicate rows
            df_cleaned = df.iloc[rows_to_keep]

            # Save back to CSV
            df_cleaned.to_csv(self.csv_path, index=False)

            duplicates_removed = original_count - len(df_cleaned)
            logger.info(f"Removed {duplicates_removed} duplicate posts from CSV")

            return duplicates_removed

        except Exception as e:
            logger.error(f"Error deduplicating posts: {e}")
            return 0