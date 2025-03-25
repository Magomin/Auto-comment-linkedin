"""
Main LinkedIn Recruiting Bot
"""
from utils.logger import setup_logger
from src.browser.selenium_browser import SeleniumBrowser
from src.linkedin.auth import LinkedInAuth
from src.linkedin.search import LinkedInSearch
from src.linkedin.scraper import LinkedInScraper
from src.comments.generator import CommentGenerator
from src.connections.linkedin_connections import LinkedInConnectionManager
from src.storage.csv_handler import CSVHandler
from src.language_prompts import detect_language
import os
from datetime import datetime
from config.settings import DEBUG_MODE
import hashlib
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

logger = setup_logger(__name__)

class LinkedInRecruitingBot:
    """Main LinkedIn Recruiting Bot class"""
    
    def __init__(self):
        """Initialize the bot components"""
        self.browser = SeleniumBrowser()
        self.auth = LinkedInAuth(self.browser)
        self.search = LinkedInSearch(self.browser)
        self.scraper = LinkedInScraper(self.browser)
        self.comment_generator = CommentGenerator()
        self.connection_manager = LinkedInConnectionManager(self.browser)
        self.storage = CSVHandler()
        self.working_selectors = {
        'comment_button': None,
        'comment_input': None,
        'submit_button': None
    }
    
    def run(self, keyword="Recruiting"):
        """
        Run the bot (legacy method, will search for a single keyword)
        
        Args:
            keyword (str): Keyword to search for
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Starting LinkedIn Recruiting Bot with keyword: {keyword}")
        
        try:
            # Initialize browser
            if not self.browser.initialize():
                logger.error("Failed to initialize browser. Aborting.")
                return False
            
            # Login to LinkedIn
            if not self.auth.login():
                logger.error("Failed to login to LinkedIn. Aborting.")
                return False
            
            # Search and scrape posts for this keyword
            posts = self.search_and_scrape(keyword)
            if not posts:
                logger.warning(f"No relevant posts found for keyword: {keyword}")
                return True
            
            logger.info(f"Found {len(posts)} relevant posts for keyword: {keyword}")
            return True
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            return False
        
        finally:
            # Ensure browser is closed
            self.browser.close()

    def search_and_scrape(self, keyword):
        """
        Search for a keyword and scrape posts with memory optimization

        Args:
        keyword (str): Keyword to search for

        Returns:
        list: List of post dictionaries
        """
        import gc  # For garbage collection
        from utils.memory_monitor import memory_warning_check, clean_memory
        
        logger.info(f"Searching and scraping posts for keyword: {keyword}")

        try:
            # Search for keyword
            if not self.search.search_keyword(keyword):
                logger.error(f"Failed to search for keyword: {keyword}. Aborting.")
                return []

            # Filter by posts
            self.search.filter_by_posts()
            # We'll continue regardless of whether the filter succeeded

            # Wait a bit longer to let the page settle
            self.browser.human_wait(3, 5)

            # Sometimes the first posts aren't relevant to our search
            # Let's scroll down a bit to load more content
            for _ in range(2):
                self.browser.human_scroll(direction=1, amount=500)
                self.browser.human_wait(1, 2)

            # Scrape posts
            posts = self.scraper.scrape_posts(keyword)
            if not posts:
                logger.warning(f"No posts found containing keyword: {keyword}")
                return []

            # Clean posts to avoid serialization issues
            clean_posts = []
            for post in posts:
                if 'post_element' in post:
                    # Save element temporarily for profile extraction
                    temp_element = post['post_element']
                    # Remove from dictionary to avoid serialization issues
                    del post['post_element']
                    # Extract profile URL before losing the element
                    author_profile_url = self.scraper._extract_profile_url_from_post(temp_element)
                    if author_profile_url:
                        post['author_profile_url'] = author_profile_url
                    # Don't keep reference to temp_element
                    temp_element = None
                clean_posts.append(post)
            
            # Replace original posts with cleaned ones
            posts = clean_posts
            # Clear the clean_posts list to free memory
            clean_posts = None
            
            # Check memory usage
            if memory_warning_check(threshold_mb=800):
                logger.warning("Memory usage high, cleaning up...")
                clean_memory()

            # Load history to avoid duplicates
            existing_posts, post_identifiers = self.storage.load_history()

            # Process posts for duplicates
            new_posts = []
            for post in posts:
                if not self.is_duplicate_post(post, post_identifiers):
                    # Additional duplicate check against existing posts
                    is_duplicate = False
                    for existing_post in existing_posts:
                        # If same author and similar content length (within 10%)
                        if (post.get('author_name') == existing_post.get('author_name') and
                            abs(len(post.get('post_content', '')) - len(existing_post.get('post_content', ''))) <
                            0.1 * len(existing_post.get('post_content', ''))):

                            # Compare content similarity
                            from difflib import SequenceMatcher
                            similarity = SequenceMatcher(None,
                                                    post.get('post_content', '')[:200],
                                                    existing_post.get('post_content', '')[:200]).ratio()

                            if similarity > 0.7:  # 70% similarity threshold
                                logger.info(f"Duplicate detected by content similarity ({similarity:.2f})")
                                is_duplicate = True
                                break

                    if not is_duplicate:
                        new_posts.append(post)

                        # Add to identifiers to prevent duplicates in the same batch
                        post_identifiers[str(post['post_id'])] = True
                        content_preview = post['post_content'][:100].lower()
                        content_hash = hashlib.md5(content_preview.encode()).hexdigest()
                        post_identifiers[content_hash] = True

            # Free memory
            posts = None
            
            # Clear existing_posts to free memory after duplicate check
            existing_posts = None
            
            # Enforce another garbage collection
            gc.collect()

            if not new_posts:
                logger.info("No new posts found.")
                return []

            logger.info(f"Found {len(new_posts)} new posts.")

            # Generate comments for new posts with language detection
            posts_with_comments = []
            for post in new_posts:
                # Use author name if available
                author_name = post.get('author_name', None)

                # Ensure author_profile_url is defined
                if 'author_profile_url' not in post:
                    post['author_profile_url'] = ""

                # Detect language of the post
                post_language = detect_language(post['post_content'])
                post['language'] = post_language

                # Try to generate a comment with quality verification
                try:
                    comment, verification = self.comment_generator.generate(
                        post['post_content'],
                        author_name,
                        force_language=post_language
                    )
                    logger.info(f"Generated comment in {post_language} with verification result: {verification}")
                except Exception as e:
                    logger.error(f"Error in comment generation: {e}")
                    comment = self.comment_generator._fallback_comment(author_name, post_language)
                    verification = "ERROR_FALLBACK"
                    logger.info(f"Using {post_language} fallback comment due to error")

                post['comment'] = comment
                post['verification'] = verification  # Store verification result
                post['commented_at'] = ""  # Empty since we're not commenting yet
                post['comment_status'] = "pending"  # Set initial comment status
                post['connection_requested'] = "false"  # Set initial connection status
                post['connection_status'] = ""  # Empty since we're not connecting yet
                posts_with_comments.append(post)

            # Debug to check fields before saving
            if posts_with_comments:
                logger.info(f"Fields in first post before saving: {list(posts_with_comments[0].keys())}")

            # Save posts with comments - use standard CSV handler method
            saved_count = self.storage.save_posts(posts_with_comments)
            logger.info(f"Saved {saved_count} posts to CSV")

            # Free memory from new_posts after saving
            new_posts = None
            
            # Check memory again and clean if needed
            clean_memory()

            return posts_with_comments

        except Exception as e:
            logger.error(f"Error searching and scraping: {e}")
            return []
        finally:
            # Ensure garbage collection happens 
            gc.collect()
    
    def post_comment(self, post_id, comment_text, language="en"):
        """
        Post a comment on a LinkedIn post with precisely focused duplicate detection
        
        Args:
        post_id (str): Post ID to identify the post in our database
        comment_text (str): Comment text to post
        language (str, optional): Language of the comment. Defaults to "en".
        
        Returns:
        bool: True if successful, False otherwise
        """
        logger.info(f"Checking post {post_id} for existing comments")
        
        try:
            # Wait for the page to load completely
            self.browser.human_wait(3, 5)
            
            # Use a more precise detection strategy
            duplicate_found = False
            try:
                from selenium.webdriver.common.by import By
                
                # First look for comment authors specifically
                comment_author_selectors = [
                    ".comments-post-meta__name",  # Comment author name element
                    ".feed-shared-comment-item__actor-link",  # Another possible author element
                    ".comments-comment-item__author-name",
                    ".comments-comment-item__profile-link",
                    ".feed-shared-comment-entity__actor-link",
                    ".comments-comment-item__name-text"
                ]
                
                # Check if any author name matches Matthieu
                for selector in comment_author_selectors:
                    try:
                        elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if "matthieu" in element.text.lower():
                                logger.info(f"Found existing comment by Matthieu using author selector: {selector}")
                                duplicate_found = True
                                break
                        if duplicate_found:
                            break
                    except:
                        continue
                        
                # If no author match, look at comment content specifically
                if not duplicate_found:
                    comment_content_selectors = [
                        ".comments-comment-item__main-content",  # Comment main content
                        ".feed-shared-comment-item__content",    # Comment content
                        ".comments-comment-item__message",       # Comment message
                        ".feed-shared-comment-entity__content",
                        ".comments-comments-list .comments-comment-item"  # Comments within the comments list
                    ]
                    
                    for selector in comment_content_selectors:
                        try:
                            elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                element_text = element.text.lower()
                                if "fribl" in element_text:
                                    logger.info(f"Found existing Fribl mention in comments using selector: {selector}")
                                    duplicate_found = True
                                    break
                            if duplicate_found:
                                break
                        except:
                            continue
                            
                # If still no match, try a deeper search using XPath to specifically target comment content
                if not duplicate_found:
                    try:
                        # Find comments section first
                        comments_containers = self.browser.driver.find_elements(
                            By.CSS_SELECTOR, 
                            ".comments-comments-list, .feed-shared-comments-list"
                        )
                        
                        for container in comments_containers:
                            # Within this container, look for text containing Fribl
                            if "fribl" in container.text.lower():
                                # More thorough check: is this inside an actual comment?
                                comment_elements = container.find_elements(By.CSS_SELECTOR, ".comments-comment-item, .feed-shared-comment-item")
                                for comment in comment_elements:
                                    if "fribl" in comment.text.lower():
                                        logger.info("Found Fribl in actual comment element")
                                        duplicate_found = True
                                        break
                        
                        if not duplicate_found and comments_containers:
                            # One more approach - check if our profile picture appears in comments
                            try:
                                # LinkedIn often shows small profile pictures for comment authors
                                # Search for profile image elements within the comments section
                                for container in comments_containers:
                                    profile_images = container.find_elements(
                                        By.CSS_SELECTOR, 
                                        ".comments-comment-item__profile-picture, .feed-shared-comment-item__profile-picture"
                                    )
                                    
                                    if profile_images:
                                        # Check alt text or other attributes that might contain your name
                                        for img in profile_images:
                                            alt_text = img.get_attribute("alt") or ""
                                            aria_label = img.get_attribute("aria-label") or ""
                                            
                                            if "matthieu" in alt_text.lower() or "matthieu" in aria_label.lower():
                                                logger.info("Found Matthieu's profile picture in comments")
                                                duplicate_found = True
                                                break
                            except:
                                pass
                    except:
                        pass
            
            except Exception as e:
                logger.debug(f"Error during comment section scan: {e}")
            
            # Short-circuit if duplicate was found
            if duplicate_found:
                logger.info(f"Already commented on post {post_id}")
                return True  # Return True to prevent marking as failed in the calling function
            
            # Continue with normal comment posting logic
            logger.info(f"No existing comment found, posting comment on post {post_id}")
            
            # Append Fribl message if enabled
            from config.settings import (
                APPEND_FRIBL_LINK,
                FRIBL_LINK_EN,
                FRIBL_LINK_FR,
                FRIBL_LINK_ES
            )

            if APPEND_FRIBL_LINK:
                # Select the appropriate link based on language
                if language.lower() == "fr":
                    fribl_link = FRIBL_LINK_FR
                elif language.lower() == "es":
                    fribl_link = FRIBL_LINK_ES
                else:  # Default to English
                    fribl_link = FRIBL_LINK_EN

                full_comment = f"{comment_text} {fribl_link}"
            else:
                full_comment = comment_text

            logger.info(f"Comment text: {full_comment}")

            # Wait longer for post to load completely
            self.browser.human_wait(3, 5)
            
            # Reset cached selectors for this post
            self.working_selectors['comment_button'] = None
            self.working_selectors['comment_input'] = None
            self.working_selectors['submit_button'] = None

            # IMPROVED APPROACH: First look for the comment text area directly
            # Sometimes we don't need to click a comment button first
            comment_input = None
            try:
                input_selectors = [
                    "div[contenteditable='true']",
                    ".ql-editor[contenteditable='true']",
                    "div.comments-comment-texteditor__content[contenteditable='true']",
                    "[data-placeholder='Add a comment…']",
                    ".comments-comment-box__form-container div[role='textbox']",
                    "div[role='textbox']",
                    ".comments-comment-box__input"
                ]

                for selector in input_selectors:
                    try:
                        elements = self.browser.wait_for_elements(selector, timeout=2)
                        for element in elements:
                            if element.is_displayed():
                                logger.info(f"Found comment input directly using selector: {selector}")
                                comment_input = element
                                # Cache the successful selector
                                self.working_selectors['comment_input'] = selector
                                break
                        if comment_input:
                            break
                    except:
                        continue
            except:
                logger.info("Could not find direct comment input, will try clicking comment button first")

            # If direct comment input not found, try to find and click "Comment" button
            if not comment_input:
                comment_button = None
                # Try many different approaches to find the comment button
                comment_buttons = [
                    "button.comments-comment-box__add-comment-button",
                    "button[aria-label='Add a comment']",
                    "button[aria-label='Comment']",
                    "button.artdeco-button--secondary",
                    ".comments-comment-box__form-container button",
                    ".social-actions button:nth-child(1)",
                    "button.feed-shared-social-action",
                    ".feed-shared-social-action--comment",
                    ".feed-shared-social-actions button",
                    ".feed-shared-social-actions span:contains('Comment')",
                    "//button[contains(., 'Comment')]",
                    "//span[contains(., 'Comment')]"
                ]

                # Try CSS selectors first
                for selector in comment_buttons:
                    if "//button" in selector or "//span" in selector:
                        continue  # Skip XPath selectors for now
                    try:
                        buttons = self.browser.wait_for_elements(selector, timeout=1)
                        for button in buttons:
                            if button.is_displayed():
                                # Check if it looks like a comment button
                                button_text = button.text.lower()
                                if "comment" in button_text:
                                    comment_button = button
                                    logger.info(f"Found comment button with text: {button_text}")
                                    break
                        if comment_button:
                            break
                    except:
                        continue

                # If still no button found, try XPath as a last resort
                if not comment_button:
                    try:
                        # Try to find any element containing "Comment" text
                        from selenium.webdriver.common.by import By
                        elements = self.browser.driver.find_elements(By.XPATH, "//button[contains(., 'Comment')] | //span[contains(., 'Comment')]")
                        for element in elements:
                            if element.is_displayed():
                                logger.info(f"Found comment button using XPath: {element.text}")
                                comment_button = element
                                break
                    except:
                        pass

                # If we found a comment button, click it
                if comment_button:
                    try:
                        self.browser.click_element(comment_button)
                        self.browser.human_wait(2, 3)
                        logger.info(f"Clicked comment button")
                    except Exception as e:
                        logger.error(f"Error clicking comment button: {e}")
                        # Try JavaScript click as a fallback
                        try:
                            self.browser.driver.execute_script("arguments[0].click();", comment_button)
                            self.browser.human_wait(2, 3)
                            logger.info("Clicked comment button using JavaScript")
                        except Exception as js_e:
                            logger.error(f"JavaScript click also failed: {js_e}")

                # Now try to find the comment input field again
                input_selectors = [
                    "div[contenteditable='true']",
                    ".ql-editor[contenteditable='true']",
                    "div.comments-comment-texteditor__content[contenteditable='true']",
                    "[data-placeholder='Add a comment…']",
                    ".comments-comment-box__form-container div[role='textbox']",
                    "div[role='textbox']",
                    ".comments-comment-box__input"
                ]

                for selector in input_selectors:
                    try:
                        elements = self.browser.wait_for_elements(selector, timeout=2)
                        for element in elements:
                            if element.is_displayed():
                                logger.info(f"Found comment input using selector: {selector}")
                                comment_input = element
                                # Cache the successful selector
                                self.working_selectors['comment_input'] = selector
                                break
                        if comment_input:
                            break
                    except:
                        continue

            # If still no comment input found, try a more aggressive approach
            if not comment_input:
                logger.warning("Could not find comment input field through normal means, trying more aggressive approach")
                try:
                    # Try to find any editable div
                    from selenium.webdriver.common.by import By
                    editable_elements = self.browser.driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")
                    for element in editable_elements:
                        if element.is_displayed():
                            logger.info("Found editable element that might be comment input")
                            comment_input = element
                            break
                except:
                    pass

            # If still no comment input found
            if not comment_input:
                logger.error("Could not find comment input field after multiple attempts")
                return False

            # Click the comment input and wait briefly
            try:
                self.browser.click_element(comment_input)
                self.browser.human_wait(1, 2)
            except Exception as e:
                logger.error(f"Error clicking comment input: {e}")
                # Try JavaScript click as a fallback
                try:
                    self.browser.driver.execute_script("arguments[0].click();", comment_input)
                    self.browser.human_wait(1, 2)
                    logger.info("Clicked comment input using JavaScript")
                except Exception as js_e:
                    logger.error(f"JavaScript click also failed: {js_e}")

            # RESTORED: Type the comment with human-like behavior
            try:
                self.browser.human_typing(comment_input, full_comment)
                self.browser.human_wait(1, 2)
            except Exception as e:
                logger.error(f"Error typing comment: {e}")
                # Try JavaScript to set the text as a fallback
                try:
                    self.browser.driver.execute_script("arguments[0].textContent = arguments[1];", comment_input, full_comment)
                    self.browser.human_wait(1, 2)
                    logger.info("Set comment text using JavaScript")
                except Exception as js_e:
                    logger.error(f"JavaScript text setting also failed: {js_e}")
                    return False

            # Try to find submit button
            submit_button = None
            submit_selectors = [
                "button.comments-comment-box__submit-button",
                "button[type='submit']",
                "button.artdeco-button--primary",
                ".comments-comment-box__submit-button",
                "button:contains('Post')",
                "button[aria-label='Post comment']",
                ".comments-comment-box__submit"
            ]

            for selector in submit_selectors:
                try:
                    elements = self.browser.wait_for_elements(selector, timeout=2)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            submit_button = element
                            logger.info(f"Found submit button using selector: {selector}")
                            break
                    if submit_button:
                        break
                except:
                    continue

            # If submit button found, click it
            if submit_button:
                try:
                    self.browser.click_element(submit_button)
                    logger.info("Clicked submit button")
                except Exception as e:
                    logger.error(f"Error clicking submit button: {e}")
                    # Try JavaScript click as a fallback
                    try:
                        self.browser.driver.execute_script("arguments[0].click();", submit_button)
                        logger.info("Clicked submit button using JavaScript")
                    except Exception as js_e:
                        logger.error(f"JavaScript click also failed: {js_e}")
            else:
                # Try multiple keyboard shortcuts as fallback
                logger.info("No submit button found, trying keyboard shortcuts")
                try:
                    from selenium.webdriver.common.keys import Keys
                    # Try Ctrl+Enter
                    comment_input.send_keys(Keys.CONTROL + Keys.ENTER)
                    self.browser.human_wait(1, 1)
                    # If that didn't work, try just Enter
                    comment_input.send_keys(Keys.ENTER)
                except Exception as e:
                    logger.error(f"Error sending keyboard shortcuts: {e}")

            # Wait to see if comment appears
            self.browser.human_wait(3, 5)

            logger.info(f"Successfully posted comment on post {post_id}")
            return True

        except Exception as e:
            logger.error(f"Error posting comment: {e}")
            return False

    
    def is_duplicate_post(self, post, post_identifiers):
        """
        Enhanced duplicate detection with multiple fallback strategies
        """
        # Check post ID
        if str(post['post_id']) in post_identifiers:
            logger.debug(f"Duplicate detected by post_id: {post['post_id']}")
            return True

        # Check URL identifier - more thorough parsing
        post_url = post.get('post_url', '')
        if '/feed/update/' in post_url:
            url_id = post_url.split('/feed/update/')[-1].split('?')[0].strip()
            if url_id in post_identifiers:
                logger.debug(f"Duplicate detected by URL ID: {url_id}")
                return True

        # Check content hash with multiple sample sizes
        for sample_size in [50, 100, 150]:
            if len(post['post_content']) >= sample_size:
                content_preview = post['post_content'][:sample_size].lower()
                content_hash = hashlib.md5(content_preview.encode()).hexdigest()
                if content_hash in post_identifiers:
                    logger.debug(f"Duplicate detected by content hash (size {sample_size})")
                    return True

        # Check author + first N words of content
        author_name = post.get('author_name', '').lower()
        if author_name and len(post['post_content']) > 20:
            first_words = ' '.join(post['post_content'].lower().split()[:10])
            author_content_key = f"{author_name}:{first_words}"
            author_content_hash = hashlib.md5(author_content_key.encode()).hexdigest()
            if author_content_hash in post_identifiers:
                logger.debug(f"Duplicate detected by author+content: {author_name}")
                return True

        # Check by date + author + content length
        post_date = post.get('post_date', '')
        content_length = len(post['post_content'])
        if post_date and author_name and content_length > 0:
            date_author_length_key = f"{post_date}:{author_name}:{content_length}"
            date_author_length_hash = hashlib.md5(date_author_length_key.encode()).hexdigest()
            if date_author_length_hash in post_identifiers:
                logger.debug(f"Duplicate detected by date+author+length")
                return True

        return False

    def run_multiple_keywords(self, keywords=None, language="en"):
        """
        Run the bot with multiple keywords, with optimizations to prevent crashes

        Args:
            keywords (list, optional): List of keywords to search for. If None, will use default keywords.
            language (str, optional): Language to use for keywords. Defaults to "en".

        Returns:
            dict: Results containing success rate and details
        """
        from config.settings import DEBUG_MODE
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
            "details": {}
        }
        
        # How many keywords to process before restarting browser
        keywords_per_session = 5
        
        try:
            # Process keywords in batches
            for i in range(0, len(keywords), keywords_per_session):
                # Get the current batch of keywords
                batch_keywords = keywords[i:i+keywords_per_session]
                logger.info(f"Processing batch {i//keywords_per_session + 1} with {len(batch_keywords)} keywords")
                
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
                        
                        # Save posts immediately 
                        keyword_success = False
                        if posts:
                            logger.info(f"Found {len(posts)} relevant posts for keyword: {keyword}")
                            # Posts are already saved in search_and_scrape
                            keyword_success = True
                        else:
                            logger.warning(f"No relevant posts found for keyword: {keyword}")
                        
                        # Update results
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
                        if DEBUG_MODE:
                            log_memory_usage()
                        
                        # Wait briefly before next keyword
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error processing keyword '{keyword}': {e}")
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
                if i + keywords_per_session < len(keywords):
                    logger.info("Waiting briefly before starting next batch...")
                    time.sleep(5)
            
            logger.info(f"Completed processing {len(keywords)} keywords")
            logger.info(f"Success rate: {results['successful_searches']}/{results['total_keywords']} ({results['successful_searches']/results['total_keywords']*100:.1f}%)")
            
            return results
            
        except Exception as e:
            logger.error(f"Error running bot with multiple keywords: {e}")
            return results
            
        finally:
            # Ensure browser is closed
            try:
                self.browser.close()
            except:
                pass