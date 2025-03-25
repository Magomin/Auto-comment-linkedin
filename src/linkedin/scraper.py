"""
LinkedIn post scraper
"""
import re
import hashlib
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from utils.logger import setup_logger
from utils.date_parser import is_post_within_time_limit, get_standard_date
from config.settings import SCROLL_COUNT
from config import settings




logger = setup_logger(__name__)

class LinkedInScraper:
    """Scrape LinkedIn posts"""
    
    def __init__(self, browser):
        """
        Initialize LinkedIn scraper
        
        Args:
            browser (SeleniumBrowser): Selenium browser instance
        """
        self.browser = browser
    

    def _extract_author_name(self, post_element):
        """Extract only first and last name from post element"""
        try:
            # Try different selectors for post author
            author_selectors = [
                ".feed-shared-actor__name",
                ".update-components-actor__name",
                ".feed-shared-actor__title",
                ".artdeco-entity-lockup__title",
                ".feed-shared-actor__container-link strong",
                ".update-components-actor__meta a",
                ".feed-shared-update-v2__description-wrapper a"
            ]
            
            for selector in author_selectors:
                try:
                    elements = post_element.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Extract the full text and process it
                        full_name_text = elements[0].text.strip()
                        
                        # Split on spaces, newlines, bullets, or other separators
                        name_parts = re.split(r'[\s\n•|]', full_name_text)
                        
                        # Filter out empty parts and get only the first two non-empty parts
                        filtered_parts = [part for part in name_parts if part.strip()]
                        if filtered_parts:
                            # Just take first two parts maximum
                            if len(filtered_parts) >= 2:
                                return f"{filtered_parts[0]} {filtered_parts[1]}"
                            else:
                                return filtered_parts[0]
                except:
                    continue
            
            return "LinkedIn User"
        except Exception as e:
            logger.error(f"Error extracting author name: {e}")
            return "LinkedIn User"


    

    def extract_post_data(self, post_element, keyword):
        """
        Extract data from a LinkedIn post element
        
        Args:
            post_element: Selenium element representing a post
            keyword (str): Keyword to check in post content
            
        Returns:
            dict or None: Post data dictionary or None if invalid
        """
        try:
            # Extract post ID (from data attribute or URL)
            post_id = self._extract_post_id(post_element)
            if not post_id:
                logger.warning("No post ID found, skipping post")
                return None
            
            # Extract post date
            post_date_text = self._extract_post_date(post_element)
            
            # Extract post content with debug logs
            post_content = self._extract_post_content(post_element)
            if not post_content or len(post_content.strip()) == 0:
                logger.warning("No post content found, skipping post")
                return None
                
            logger.debug(f"CONTENT EXTRACTED: {post_content[:100]}...")
            
            # Extract author name
            author_name = self._extract_author_name(post_element)
            if not author_name:
                logger.warning("No author name found, using default")
                author_name = "LinkedIn User"
        
            # Extract post URL
            post_url = self._extract_post_url(post_element, post_id)
            if not post_url:
                logger.warning("No post URL found, skipping post")
                return None
            
            # Force all posts to be considered relevant for debug
            # Instead of checking keywords, just log them
            logger.debug(f"KEYWORD CHECK: '{keyword}' against post content")
            
            # Check if keyword is in post content (case insensitive)
            if keyword.lower() not in post_content.lower():
                logger.debug(f"Post does not contain keyword '{keyword}'")
                # Uncomment if you want to filter by keyword:
                # return None
            
            return {
                "post_id": post_id,
                "post_date": get_standard_date(),
                "post_date_text": post_date_text,
                "post_content": post_content,
                "author_name": author_name,
                "post_url": post_url
            }
            
        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            return None

    def _extract_post_id(self, post_element):
        """Extract post ID with improved consistency"""
        try:
            # Try to get ID from data attribute
            post_id = post_element.get_attribute("data-urn") or post_element.get_attribute("id")

            # If we have a direct ID, use it
            if post_id:
                # Clean up the ID to ensure consistency
                if "urn:li:activity:" in post_id:
                    # Extract just the activity ID part
                    return post_id.split("urn:li:activity:")[-1]
                return post_id

            # Try to extract from URL if available
            try:
                # Look for any link that might contain a post URL
                link_elements = post_element.find_elements(By.CSS_SELECTOR, "a[href*='/feed/update/']")
                if link_elements:
                    href = link_elements[0].get_attribute("href")
                    if '/feed/update/' in href:
                        url_id = href.split('/feed/update/')[-1].split('?')[0].strip()
                        return url_id
            except:
                pass

            # If still no ID, generate a more stable one based on content and author
            try:
                # Get content
                content_elements = post_element.find_elements(By.CSS_SELECTOR,
                    ".feed-shared-update-v2__description-wrapper, .feed-shared-text, .update-components-text")

                content = ""
                for elem in content_elements:
                    if elem.text:
                        content += elem.text

                # Get author
                author_elements = post_element.find_elements(By.CSS_SELECTOR,
                    ".feed-shared-actor__name, .update-components-actor__name")

                author = ""
                if author_elements:
                    author = author_elements[0].text

                # Create a stable ID from author + first 100 chars of content
                if content:
                    stable_id = f"{author}:{content[:100]}"
                    return f"post_{hashlib.md5(stable_id.encode()).hexdigest()}"
            except:
                pass

            # Last resort - use element attributes as a basis
            element_attrs = ""
            try:
                for attr in ["class", "role", "aria-label"]:
                    attr_value = post_element.get_attribute(attr)
                    if attr_value:
                        element_attrs += attr_value

                return f"post_{hashlib.md5(element_attrs.encode()).hexdigest()}"
            except:
                # Absolute last resort
                return f"unknown_post_{hashlib.md5(str(post_element).encode()).hexdigest()}"

        except Exception as e:
            logger.error(f"Error extracting post ID: {e}")
            return f"unknown_post_{hashlib.md5(str(post_element).encode()).hexdigest()}"
        
    def _extract_post_date(self, post_element):
        """Extract post date from post element"""
        try:
            # Try to find date element using various selectors
            selectors = [
                ".feed-shared-actor__sub-description",
                ".update-components-actor__sub-description",
                ".artdeco-entity-lockup__caption"
            ]
            
            for selector in selectors:
                try:
                    post_date_elem = post_element.find_element(By.CSS_SELECTOR, selector)
                    # LinkedIn date format: "Author name • Title • Date"
                    post_date_text = post_date_elem.text.strip()
                    
                    # Extract the last part after the bullet points
                    if "•" in post_date_text:
                        post_date_text = post_date_text.split("•")[-1].strip()
                    
                    return post_date_text
                except:
                    continue
            
            # If no date found
            return "Unknown"
        except Exception as e:
            logger.error(f"Error extracting post date: {e}")
            return "Unknown"
    
    def _extract_post_content(self, post_element):
        """Extract post content from post element"""
        try:
            # Try different selectors for post content
            content_selectors = [
                        ".feed-shared-update-v2__description-wrapper",
                ".update-components-text",
                ".feed-shared-text",
                ".feed-shared-update-v2__commentary",
                ".feed-shared-inline-show-more-text",
                ".feed-shared-text__text-view",
                ".update-components-update-v2__commentary",
                ".update-components-text relative",
                ".search-content__entity-result",
                ".visually-hidden",
                "span[dir='ltr']",
                ".break-words",
                "p",
                ".artdeco-card p"
            ]
            
            for selector in content_selectors:
                try:
                    elements = post_element.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        content = " ".join([elem.text for elem in elements if elem.text])
                        if content.strip():
                            return content
                except:
                    continue
            
            # If no content found with specific selectors, get all text
            return post_element.text
        except Exception as e:
            logger.error(f"Error extracting post content: {e}")
            return "No content extracted"

    # Find this method in src/linkedin/scraper.py:
    def _extract_post_url(self, post_element, post_id):
        """Extract post URL from post element with enhanced URL finding capability"""
        try:
            # Try to find a direct link in the post using multiple approaches
            try:
                # Approach 1: Look for specific link selectors that might contain post URLs
                link_selectors = [
                    "a.app-aware-link[href*='/feed/update/']",
                    "a[href*='/feed/update/']",
                    "a.feed-shared-update-v2__permalink",
                    "a.update-components-actor__sub-description-link",
                    "a.update-components-actor__container-link",
                    "a.feed-shared-actor__container-link",
                    "a.feed-shared-update-v2__social-action-text",
                    "a.comments-post-meta__author-name",
                    "a.feed-shared-text-view a",
                    "article a"
                ]
                
                for selector in link_selectors:
                    try:
                        links = post_element.find_elements(By.CSS_SELECTOR, selector)
                        if links:
                            for link in links:
                                href = link.get_attribute("href")
                                if href and '/feed/update/' in href:
                                    logger.debug(f"Found URL using selector: {selector}")
                                    return href
                    except Exception as e:
                        logger.debug(f"Error with selector {selector}: {e}")
                        continue
                        
                # Approach 2: Try to find ANY link in the post that contains 'feed/update'
                try:
                    all_links = post_element.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        href = link.get_attribute("href")
                        if href and '/feed/update/' in href:
                            logger.debug("Found URL in generic link search")
                            return href
                except Exception as e:
                    logger.debug(f"Error in generic link search: {e}")
                    
                # Approach 3: Look for data attributes that might contain post IDs
                try:
                    data_id = post_element.get_attribute("data-id")
                    if data_id and ":" in data_id:
                        activity_id = data_id.split(":")[-1]
                        url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}"
                        logger.debug("Created URL from data-id attribute")
                        return url
                except Exception as e:
                    logger.debug(f"Error extracting from data attributes: {e}")
                    
                # Approach 4: Try to find the post ID in the HTML content
                try:
                    html_content = post_element.get_attribute("outerHTML")
                    if html_content:
                        # Look for patterns like "urn:li:activity:1234567890"
                        import re
                        activity_matches = re.findall(r'urn:li:activity:(\d+)', html_content)
                        if activity_matches:
                            activity_id = activity_matches[0]
                            url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}"
                            logger.debug("Created URL from HTML content regex")
                            return url
                except Exception as e:
                    logger.debug(f"Error extracting from HTML content: {e}")
            except Exception as e:
                logger.debug(f"Error in URL extraction approaches: {e}")
                
            # If all else fails, use the post_id to construct a URL
            if post_id:
                # Case 1: Already contains full URN format
                if "urn:li:activity:" in post_id:
                    url = f"https://www.linkedin.com/feed/update/{post_id}"
                    logger.debug("Created URL from post_id with URN")
                    return url
                    
                # Case 2: Contains activity ID without URN prefix
                elif post_id.isdigit():
                    url = f"https://www.linkedin.com/feed/update/urn:li:activity:{post_id}"
                    logger.debug("Created URL from numeric post_id")
                    return url
                    
                # Case 3: post_id is a generated hash - can't create reliable URL
                # Instead of returning None, create a URL with disclaimer
                else:
    # Don't create URLs for hashed post_ids as they won't work
                    logger.debug(f"Cannot create reliable URL from hash post_id: {post_id}")
                return None
                    
            logger.warning("Could not extract or create a post URL")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting post URL: {e}")
            # Last resort - create any URL rather than none

            return None
    
    def _extract_profile_url_from_post(self, post_element):
        """
        Extract the profile URL from a post element
        
        Args:
            post_element: Selenium element representing a post
            
        Returns:
            str or None: Profile URL or None if not found
        """
        if not post_element:
            return None
            
        try:
            # Try different selectors for profile links
            profile_link_selectors = [
                ".feed-shared-actor__container-link",
                ".update-components-actor__container-link",
                ".update-components-actor__meta a",
                ".feed-shared-update-v2__description-wrapper a",
                ".feed-shared-actor__title a",
                ".update-components-actor__sub-description-link"
            ]
            
            for selector in profile_link_selectors:
                try:
                    links = post_element.find_elements(By.CSS_SELECTOR, selector)
                    if links:
                        for link in links:
                            href = link.get_attribute("href")
                            if href and ("/in/" in href or "/pub/" in href):
                                return href
                except Exception as e:
                    logger.debug(f"Error finding profile link with selector {selector}: {e}")
                    continue
            
            # If no direct profile link found, try to extract from the post header
            try:
                # Try to find the author section of the post
                author_sections = post_element.find_elements(By.CSS_SELECTOR, 
                    ".feed-shared-actor, .update-components-actor, .feed-shared-actor__container")
                
                for section in author_sections:
                    links = section.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and ("/in/" in href or "/pub/" in href):
                            return href
            except Exception as e:
                logger.debug(f"Error extracting profile URL from author section: {e}")
            
            return None
                
        except Exception as e:
            logger.error(f"Error extracting profile URL from post: {e}")
            return None

    def scrape_posts(self, keyword):
        """
        Scrape LinkedIn posts containing keyword with duplicate detection
        
        Args:
        keyword (str): Keyword to search for in posts
        
        Returns:
        list: List of post data dictionaries
        """
        logger.info(f"Scraping posts containing keyword: {keyword}")
        posts = []
        
        try:
            # Load existing post identifiers for duplicate detection
            from src.storage.csv_handler import CSVHandler
            csv_handler = CSVHandler()
            _, post_identifiers = csv_handler.load_history()
            
            # Find post elements
            post_selectors = [
                ".feed-shared-update-v2",
                ".occludable-update",
                ".search-result__occluded-item",
                ".search-content__result",
                ".feed-shared-update",
                ".update-components-actor",
                "div[data-id]",
                "[data-urn]",
                ".artdeco-card"
            ]
            
            post_elements = []
            for selector in post_selectors:
                post_elements = self.browser.wait_for_elements(selector)
                if post_elements:
                    logger.info(f"Found {len(post_elements)} posts with selector: {selector}")
                    break
            
            if not post_elements:
                logger.error("No posts found with any selector")
                return posts
            
            logger.info(f"Found {len(post_elements)} posts")
            
            # Track posts we've already seen in this session to avoid duplicates
            seen_posts = {}
            
            # Scroll to load more posts
            for i in range(SCROLL_COUNT):  # Make sure to import SCROLL_COUNT from settings
                logger.info(f"Scroll {i+1}/{SCROLL_COUNT}")
                
                # Scroll down
                self.browser.human_scroll(direction=1, amount=800)
                
                # Wait for new posts to load
                self.browser.human_wait()
                
                # Get updated list of posts
                for selector in post_selectors:
                    new_post_elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                    if new_post_elements and len(new_post_elements) > len(post_elements):
                        post_elements = new_post_elements
                        logger.info(f"After scroll {i+1}: {len(post_elements)} posts")
                        break
            
            # Process posts
            for post in post_elements:
                try:
                    # Extract basic data first to check for duplicates
                    try:
                        post_id = self._extract_post_id(post)
                        post_content = self._extract_post_content(post)
                        author_name = self._extract_author_name(post)
                        post_url = self._extract_post_url(post, post_id)
                        
                        # Skip if any essential field is None
                        if not post_id or not post_content or not author_name:
                            logger.warning("Skipping post with missing essential data")
                            continue
                            
                        # Create a minimal post object for duplicate checking
                        post_data = {
                            "post_id": post_id,
                            "post_content": post_content,
                            "author_name": author_name,
                            "post_url": post_url
                        }
                    except Exception as e:
                        logger.error(f"Error extracting basic post data: {e}")
                        continue
                    
                    # Check if this is a duplicate using the bot's method
                    # First check against already seen posts in this session
                    content_preview = post_content[:100].lower() if post_content else ""
                    content_hash = hashlib.md5(content_preview.encode()).hexdigest()
                    
                    if content_hash in seen_posts:
                        logger.info(f"Skipping duplicate post (seen in this session)")
                        continue
                    
                    # Then check against historical posts using direct checks instead of the bot method
                    # Replace this part in the scrape_posts method:
                    try:
                        # Use a direct function call to the static method instead
                        is_duplicate = False
                        
                        # Use plain dictionary lookup for post_id - ensure it's a string
                        if str(post_id) in post_identifiers:
                            is_duplicate = True
                            logger.debug(f"Duplicate detected by post_id: {post_id}")
                        
                        # Use URL check as fallback
                        elif post_url and '/feed/update/' in post_url:
                            url_id = post_url.split('/feed/update/')[-1].split('?')[0].strip()
                            if url_id in post_identifiers:
                                is_duplicate = True
                                logger.debug(f"Duplicate detected by URL ID: {url_id}")
                        
                        # Use content preview check as another fallback
                        if content_hash in post_identifiers:
                            is_duplicate = True
                            logger.debug(f"Duplicate detected by content hash")
                        
                        if is_duplicate:
                            logger.info(f"Skipping duplicate post (found in history)")
                            continue
                    except Exception as e:
                        logger.error(f"Error in duplicate detection: {e}")
                        # Continue with this post anyway since we couldn't verify if it's a duplicate
                        
                    
                    # If we get here, it's not a duplicate, so extract full data
                    post_data = self.extract_post_data(post, keyword)
                    if post_data:
                        # Mark as seen to avoid duplicates in the same batch
                        seen_posts[content_hash] = True
                        
                        # Add the post element for profile URL extraction
                        post_data['post_element'] = post
                        
                        posts.append(post_data)
                        logger.info(f"Found relevant post: {post_data['post_content'][:50]}...")
                except Exception as e:
                    logger.error(f"Error processing post: {e}")
            
            logger.info(f"Scraped {len(posts)} relevant posts out of {len(post_elements)} total posts")
            
        except Exception as e:
            logger.error(f"Error scraping posts: {e}")
        
        return posts