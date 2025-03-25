"""
Selenium browser wrapper with human-like behavior
"""
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from config.settings import USER_AGENT, HEADLESS, MIN_WAIT_TIME, MAX_WAIT_TIME, MIN_TYPE_DELAY, MAX_TYPE_DELAY
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SeleniumBrowser:
    """Selenium browser wrapper with human-like behavior"""
    
    def __init__(self):
        """Initialize browser instance"""
        self.driver = None
    
    def initialize(self):
        """
        Initialize browser with anti-detection and human-like settings
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            options = webdriver.ChromeOptions()
            
            # Basic settings
            options.add_argument("--start-maximized")
            
            # Headless mode if configured
            if HEADLESS:
                options.add_argument("--headless")
                options.add_argument("--window-size=1920,1080")
            
            # Anti-bot detection settings
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            
            # Initialize driver
            self.driver = webdriver.Chrome(options=options)
            
            # Set user agent
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": USER_AGENT
            })
            
            # Hide automation flags
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Browser initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    def close(self):
        """Close browser instance"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
    
    def navigate_to(self, url):
        """
        Navigate to URL with human-like behavior
        
        Args:
            url (str): URL to navigate to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.driver.get(url)
            self.human_wait()
            logger.info(f"Navigated to {url}")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return False
    
    def human_typing(self, element, text):
        """
        Type text into an element with a human-like delay
        
        Args:
            element: WebElement to type into
            text (str): Text to type
            
        Returns:
            None
        """
        try:
            from config.settings import MIN_TYPE_DELAY, MAX_TYPE_DELAY
            
            # Type character by character with random delays
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(MIN_TYPE_DELAY, MAX_TYPE_DELAY))
            
            # Check if Fribl link was correctly added
            try:
                actual_text = element.text or element.get_attribute("value") or element.get_attribute("textContent") or ""
                if "fribl.co" not in actual_text.lower() and "fribl.co" in text.lower():
                    logger.warning("Fribl link might be missing from input - checking again after delay")
                    time.sleep(1)  # Wait a bit and check again
                    
                    actual_text = element.text or element.get_attribute("value") or element.get_attribute("textContent") or ""
                    if "fribl.co" not in actual_text.lower():
                        logger.warning("Fribl link is definitely missing, attempting to add it again")
                        # Just append the Fribl link part to whatever is there
                        if "It's Free btw" in text:
                            element.send_keys(" It's Free btw https://www.app.fribl.co/login")
                        else:
                            element.send_keys(" https://www.app.fribl.co/login")
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error during human typing: {e}")
            raise

    def human_scroll(self, direction=None, amount=None):
        """
        Perform random scrolling to mimic human behavior
        
        Args:
            direction (int, optional): Scroll direction (1 for down, -1 for up)
            amount (int, optional): Scroll amount in pixels
        
        """
        try:
            # Use provided values or generate random ones
            scroll_amount = amount or random.randint(300, 700)
            scroll_direction = direction or random.choice([1, -1])
            
            self.driver.execute_script(f"window.scrollBy(0, {scroll_direction * scroll_amount});")
            time.sleep(random.uniform(0.5, 2.0))
            
            logger.debug(f"Scrolled {scroll_direction * scroll_amount} pixels")
        except Exception as e:
            logger.error(f"Error during human scrolling: {e}")
    
    def human_wait(self, min_time=None, max_time=None):
        """
        Wait for a random time to mimic human behavior
        
        Args:
            min_time (float, optional): Minimum wait time in seconds
            max_time (float, optional): Maximum wait time in seconds
        """
        # Use provided values or default from settings
        min_t = min_time if min_time is not None else MIN_WAIT_TIME
        max_t = max_time if max_time is not None else MAX_WAIT_TIME
        
        wait_time = random.uniform(min_t, max_t)
        time.sleep(wait_time)
        
        logger.debug(f"Waited for {wait_time:.2f} seconds")


    def wait_for_element(self, selector, by=By.CSS_SELECTOR, timeout=10):
        """
        Wait for an element to be present
        
        Args:
            selector (str): Element selector
            by: Selector type (By.CSS_SELECTOR, By.XPATH, etc.)
            timeout (int): Maximum wait time in seconds
            
        Returns:
            WebElement: Found element or None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            logger.debug(f"Found element: {selector}")
            return element
        except Exception as e:
            logger.error(f"Element not found: {selector}, Error: {e}")
            return None
    
    def wait_for_elements(self, selector, by=By.CSS_SELECTOR, timeout=10):
        """
        Wait for elements to be present
        
        Args:
            selector (str): Element selector
            by: Selector type (By.CSS_SELECTOR, By.XPATH, etc.)
            timeout (int): Maximum wait time in seconds
            
        Returns:
            list: List of found elements or empty list
        """
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((by, selector))
            )
            logger.debug(f"Found {len(elements)} elements: {selector}")
            return elements
        except Exception as e:
            logger.error(f"Elements not found: {selector}, Error: {e}")
            return []
    
    def wait_for_clickable(self, selector, by=By.CSS_SELECTOR, timeout=10):
        """
        Wait for an element to be clickable
        
        Args:
            selector (str): Element selector
            by: Selector type (By.CSS_SELECTOR, By.XPATH, etc.)
            timeout (int): Maximum wait time in seconds
            
        Returns:
            WebElement: Found element or None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            logger.debug(f"Element is clickable: {selector}")
            return element
        except Exception as e:
            logger.error(f"Element not clickable: {selector}, Error: {e}")
            return None
    
    def click_element(self, element):
        """
        Click an element with human-like behavior
        
        Args:
            element: Selenium element to click
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            element.click()
            self.human_wait(0.5, 1.5)  # Short wait after click
            logger.debug("Clicked element")
            return True
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return False
    
    def hover_element(self, element):
        """
        Hover over an element
        
        Args:
            element: Selenium element to hover over
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            self.human_wait(0.5, 1.0)  # Short wait after hover
            logger.debug("Hovered over element")
            return True
        except Exception as e:
            logger.error(f"Failed to hover over element: {e}")
            return False

    def save_page_source(self, name):
        """Save current page HTML for debugging"""
        if not self.driver:
            return
            
        try:
            from config.settings import DEBUG_MODE, HTML_DUMP_DIR
            
            if not DEBUG_MODE:
                return
                
            # Ensure directory exists
            os.makedirs(HTML_DUMP_DIR, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(HTML_DUMP_DIR, f"{name}_{timestamp}.html")
            
            # Save page source
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
                
            logger.info(f"Saved page source: {filename}")
        except Exception as e:
            logger.error(f"Failed to save page source: {e}")