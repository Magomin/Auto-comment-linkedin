"""
LinkedIn connection manager for sending connection requests
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from utils.logger import setup_logger
from src.storage.csv_handler import CSVHandler
from config.settings import CONNECTION_WEEKLY_LIMIT, MIN_WAIT_TIME, MAX_WAIT_TIME

logger = setup_logger(__name__)

class LinkedInConnectionManager:
    """Manage LinkedIn connection requests"""
    
    def __init__(self, browser):
        """
        Initialize LinkedIn connection manager
        
        Args:
            browser (SeleniumBrowser): Selenium browser instance
        """
        self.browser = browser
        self.storage = CSVHandler()
        self.weekly_limit = CONNECTION_WEEKLY_LIMIT
    
    def can_send_invitation(self):
        """
        Check if we can send more invitations this week
        
        Returns:
            bool: True if we can send more invitations, False otherwise
        """
        # Get count of connection requests sent this week
        weekly_count = self.storage.get_weekly_connection_count()
        
        logger.info(f"Connection requests sent this week: {weekly_count}/{self.weekly_limit}")
        
        # Check if we've reached the weekly limit
        return weekly_count < self.weekly_limit
    
    def visit_profile(self, profile_url):
        """
        Visit a LinkedIn profile
        
        Args:
            profile_url (str): LinkedIn profile URL
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Visiting profile: {profile_url}")
        
        try:
            # Navigate to profile
            if not self.browser.navigate_to(profile_url):
                logger.error("Failed to navigate to profile")
                return False
            
            # Wait for page to load
            self.browser.human_wait(MIN_WAIT_TIME, MAX_WAIT_TIME)
            
            # Check if we're on a profile page
            profile_content = self.browser.wait_for_element(".pv-top-card", timeout=10)
            if not profile_content:
                logger.warning("Profile page did not load correctly")
                return False
            
            logger.info("Successfully visited profile")
            return True
            
        except Exception as e:
            logger.error(f"Error visiting profile: {e}")
            return False
    
    def extract_profile_id(self, profile_url):
        """
        Extract the LinkedIn profile ID from the URL
        
        Args:
            profile_url (str): LinkedIn profile URL
            
        Returns:
            str: Profile ID or None if not found
        """
        try:
            # Common patterns for LinkedIn profile URLs
            if "/in/" in profile_url:
                # Example: https://www.linkedin.com/in/username/
                return profile_url.split("/in/")[-1].rstrip("/")
            elif "/pub/" in profile_url:
                # Example: https://www.linkedin.com/pub/username/
                return profile_url.split("/pub/")[-1].rstrip("/")
            else:
                # Generate a unique ID based on the URL
                import hashlib
                return f"profile_{hashlib.md5(profile_url.encode()).hexdigest()[:10]}"
                
        except Exception as e:
            logger.error(f"Error extracting profile ID: {e}")
            return None
    
    def extract_profile_details(self):
        """
        Extract details from a profile page
        
        Returns:
            dict: Profile details or None if not found
        """
        try:
            # Get profile name
            name_element = self.browser.wait_for_element(".pv-top-card h1", By.CSS_SELECTOR)
            name = name_element.text if name_element else "LinkedIn User"
            
            # Get profile URL
            current_url = self.browser.driver.current_url
            
            # Get profile ID
            profile_id = self.extract_profile_id(current_url)
            
            return {
                "profile_id": profile_id,
                "profile_url": current_url,
                "name": name
            }
            
        except Exception as e:
            logger.error(f"Error extracting profile details: {e}")
            return None
    
    def send_connection_request(self, profile_url=None, custom_note=None, keyword=None):
        """
        Send a connection request
        
        Args:
            profile_url (str, optional): LinkedIn profile URL. If None, uses current page.
            custom_note (str, optional): Custom note to include with request. Defaults to None.
            keyword (str, optional): Keyword used to find this connection. Defaults to None.
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if we can send more invitations
        if not self.can_send_invitation():
            logger.warning("Weekly connection limit reached. Skipping connection request.")
            return False
        
        try:
            # If profile URL is provided, visit the profile first
            if profile_url and not self.visit_profile(profile_url):
                return False
            
            # Extract profile details (from current page)
            profile_details = self.extract_profile_details()
            if not profile_details:
                logger.error("Failed to extract profile details")
                return False
            
            # Look for Connect button
            connect_button_selectors = [
                "button.pv-s-profile-actions--connect",
                "button.artdeco-button--primary",
                "button[aria-label*='Connect']",
                "button.artdeco-button[aria-label*='connect']",
                "button.pv-s-profile-actions__overflow-toggle",  # More button
                ".pvs-profile-actions button",
                ".pvs-profile-actions [aria-label*='Connect']"
            ]
            
            connect_button = None
            for selector in connect_button_selectors:
                try:
                    elements = self.browser.wait_for_elements(selector, timeout=2)
                    if elements:
                        for element in elements:
                            if "connect" in element.text.lower() or "connect" in element.get_attribute("aria-label").lower():
                                connect_button = element
                                break
                    if connect_button:
                        break
                except:
                    continue
            
            # If we found a More button but not the Connect button directly
            if not connect_button:
                try:
                    more_button = self.browser.wait_for_element("button.pv-s-profile-actions__overflow-toggle", timeout=2)
                    if more_button:
                        self.browser.click_element(more_button)
                        self.browser.human_wait(1, 2)
                        
                        # Look for Connect option in dropdown
                        connect_options = self.browser.wait_for_elements("div.pv-s-profile-actions__overflow-dropdown li button", timeout=2)
                        for option in connect_options:
                            if "connect" in option.text.lower():
                                connect_button = option
                                break
                except:
                    pass
            
            if not connect_button:
                logger.warning("Connect button not found. User may already be connected.")
                return False
            
            # Click the Connect button
            self.browser.click_element(connect_button)
            self.browser.human_wait(1, 2)
            
            # Check if there's an Add Note button (optional for sending a custom note)
            if custom_note:
                try:
                    add_note_button = self.browser.wait_for_element("button[aria-label*='Add a note']", timeout=3)
                    if add_note_button:
                        self.browser.click_element(add_note_button)
                        self.browser.human_wait(1, 2)
                        
                        # Find text area and type note
                        note_textarea = self.browser.wait_for_element("textarea#custom-message", timeout=3)
                        if note_textarea:
                            self.browser.human_typing(note_textarea, custom_note)
                            self.browser.human_wait(1, 2)
                except Exception as e:
                    logger.warning(f"Failed to add custom note: {e}")
            
            # Find and click the Send/Connect button
            send_button_selectors = [
                "button[aria-label*='Send now']",
                "button[aria-label*='Send invitation']",
                "button[aria-label*='Connect']",
                "button.artdeco-button--primary"
            ]
            
            send_button = None
            for selector in send_button_selectors:
                try:
                    send_button = self.browser.wait_for_element(selector, timeout=2)
                    if send_button:
                        break
                except:
                    continue
            
            if not send_button:
                logger.warning("Send button not found")
                # Try to close any open dialogs to continue
                self.browser.try_close_dialogs()
                return False
            
            # Click the Send button
            self.browser.click_element(send_button)
            self.browser.human_wait(1, 2)
            
            # Save the connection in our database
            self.storage.save_connection(
                profile_details["profile_id"],
                profile_details["profile_url"],
                profile_details["name"],
                status="sent",
                notes=custom_note or "",
                keyword=keyword or ""
            )
            
            logger.info(f"Successfully sent connection request to {profile_details['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending connection request: {e}")
            # Try to close any open dialogs to continue
            self.browser.try_close_dialogs()
            return False
    
    def extract_profile_url_from_post(self, post_element):
        """
        Extract profile URL from a post element
        
        Args:
            post_element: Selenium element representing a post
            
        Returns:
            str or None: Profile URL or None if not found
        """
        try:
            # Try different selectors for profile links
            profile_link_selectors = [
                ".feed-shared-actor__container-link",
                ".update-components-actor__container-link",
                ".update-components-actor__meta a",
                ".feed-shared-update-v2__description-wrapper a",
                ".feed-shared-actor__title a"
            ]
            
            for selector in profile_link_selectors:
                try:
                    links = post_element.find_elements(By.CSS_SELECTOR, selector)
                    if links:
                        for link in links:
                            href = link.get_attribute("href")
                            if href and ("/in/" in href or "/pub/" in href):
                                return href
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting profile URL from post: {e}")
            return None
    
    def get_fribl_connection_note(self, author_name, keyword=None):
        """
        Generate a personalized connection note
        
        Args:
            author_name (str): Name of the person to connect with
            keyword (str, optional): Keyword used to find this connection. Defaults to None.
            
        Returns:
            str: Personalized connection note
        """
        # Get first name
        first_name = author_name.split()[0] if author_name and " " in author_name else author_name
        
        base_note = f"Hi {first_name}, I came across your post about "
        if keyword:
            base_note += f"{keyword.lower()} "
        base_note += "and found it valuable. I work at Fribl, we specialize in AI talent recruitment. Would love to connect professionally!"
        
        # Ensure the note is within LinkedIn's character limit (300 characters)
        if len(base_note) > 300:
            base_note = base_note[:297] + "..."
        
        return base_note