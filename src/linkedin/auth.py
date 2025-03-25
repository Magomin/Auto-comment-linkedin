"""
LinkedIn authentication module
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from config.settings import LINKEDIN_LOGIN_URL
from config.credentials import LINKEDIN_USERNAME, LINKEDIN_PASSWORD
from utils.logger import setup_logger

logger = setup_logger(__name__)

class LinkedInAuth:
    """Handle LinkedIn authentication"""
    
    def __init__(self, browser):
        """
        Initialize LinkedIn authentication
        
        Args:
            browser (SeleniumBrowser): Selenium browser instance
        """
        self.browser = browser
    
    def login(self):
        """
        Login to LinkedIn
        
        Returns:
            bool: True if login successful, False otherwise
        """
        logger.info("Attempting to login to LinkedIn")
        
        # Navigate to login page
        if not self.browser.navigate_to(LINKEDIN_LOGIN_URL):
            logger.error("Failed to navigate to LinkedIn login page")
            return False
        
        try:
            # Enter username
            username_input = self.browser.wait_for_element("input#username", By.CSS_SELECTOR)
            if not username_input:
                logger.error("Username input field not found")
                return False
            
            self.browser.human_typing(username_input, LINKEDIN_USERNAME)
            
            # Enter password
            password_input = self.browser.wait_for_element("input#password", By.CSS_SELECTOR)
            if not password_input:
                logger.error("Password input field not found")
                return False
            
            self.browser.human_typing(password_input, LINKEDIN_PASSWORD)
            
            # Click login button
            login_button = self.browser.wait_for_element("button[type='submit']")
            if not login_button:
                logger.error("Login button not found")
                return False
            
            self.browser.click_element(login_button)
            
            # Wait for login to complete
            nav_element = self.browser.wait_for_element(".global-nav__content", timeout=15)
            if not nav_element:
                logger.error("Login failed: Navigation element not found after login")
                return False
            
            self.browser.human_wait()
            logger.info("Successfully logged in to LinkedIn")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def is_logged_in(self):
        """
        Check if user is logged in to LinkedIn
        
        Returns:
            bool: True if logged in, False otherwise
        """
        try:
            # Check for navigation element that's only present when logged in
            nav_element = self.browser.wait_for_element(".global-nav__content", timeout=5)
            return nav_element is not None
        except Exception:
            return False