"""
LinkedIn search functionality
"""
import sys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from utils.logger import setup_logger

logger = setup_logger(__name__)

class LinkedInSearch:
    """Handle LinkedIn search operations"""
    
    def __init__(self, browser):
        """
        Initialize LinkedIn search
        
        Args:
            browser (SeleniumBrowser): Selenium browser instance
        """
        self.browser = browser
    


    def clear_search_field(self):
        """
        Clear the LinkedIn search input field
        
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Clearing search field")
        
        try:
            # Find search box
            search_box = self.browser.wait_for_element(".search-global-typeahead__input")
            if not search_box:
                logger.error("Search box not found")
                return False
            
            # Try to clear using Selenium's clear method first
            try:
                search_box.clear()
                self.browser.human_wait(0.5, 1)
                if not search_box.get_attribute("value"):
                    logger.info("Successfully cleared search field")
                    return True
            except Exception as e:
                logger.debug(f"Clear method failed: {e}")
            
            # If clear() didn't work, try click and delete
            try:
                # Click on search box to focus it
                self.browser.click_element(search_box)
                self.browser.human_wait(0.5, 1)
                
                # Press CTRL+A to select all text
                search_box.send_keys(Keys.CONTROL + "a")
                # Press DELETE to delete the text
                search_box.send_keys(Keys.DELETE)
                
                self.browser.human_wait(0.5, 1)
                
                # Verify if cleared
                if not search_box.get_attribute("value"):
                    logger.info("Successfully cleared search field with keyboard")
                    return True
            except Exception as e:
                logger.debug(f"Keyboard clear method failed: {e}")
            
            logger.warning("Failed to clear search field")
            return False
            
        except Exception as e:
            logger.error(f"Error clearing search field: {e}")
            return False



    def search_keyword(self, keyword):
        """
        Search for keyword on LinkedIn
        
        Args:
            keyword (str): Keyword to search for
            
        Returns:
            bool: True if search successful, False otherwise
        """
        logger.info(f"Searching for keyword: {keyword}")
        
        try:
            # Find search box
            search_box = self.browser.wait_for_element(".search-global-typeahead__input")
            if not search_box:
                logger.error("Search box not found")
                return False
            
            # Click on search box
            self.browser.click_element(search_box)
            self.browser.human_wait()
            
            # Type search keyword
            self.browser.human_typing(search_box, keyword)
            self.browser.human_wait()
            
            # Press Enter
            search_box.send_keys(Keys.ENTER)
            self.browser.human_wait()
            
            # Wait for search results
            results_container = self.browser.wait_for_element(".search-results-container", timeout=15)
            if not results_container:
                logger.error("Search results container not found")
                return False
            
            logger.info(f"Successfully searched for '{keyword}'")
            return True
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return False
    
    def filter_by_posts(self):
        """
        Filter search results to show only posts
        
        Returns:
            bool: True if filter successful, False otherwise
        """
        logger.info("Filtering search results to show only posts")
        
        # Wait a bit longer for all elements to load
        self.browser.human_wait(3, 6)
        # Save page source for debugging
        self.browser.save_page_source("search_results_before_filter")
        
        try:
            # Debug: Try to find all available filters/tabs
            available_tabs = []
            try:
                # Try to find all tab elements on the search page
                tab_elements = self.browser.driver.find_elements(By.CSS_SELECTOR, 
                                                           ".search-reusables__filter-pill-button, .artdeco-pill, .search-reusables__filter-pill")
                for tab in tab_elements:
                    try:
                        tab_text = tab.text
                        available_tabs.append(tab_text)
                    except:
                        pass
                
                logger.info(f"Available tabs/filters: {', '.join(available_tabs) if available_tabs else 'None found'}")
            except Exception as e:
                logger.warning(f"Could not enumerate tabs: {e}")
            
            # List of possible selectors for the Posts filter button
            post_filter_selectors = [
                # XPath selectors
                ("//button[contains(text(), 'Posts')]", By.XPATH),
                ("//a[contains(@href, 'content-filter=updates')]", By.XPATH),
                ("//button[contains(@aria-label, 'Posts')]", By.XPATH),
                ("//button[contains(., 'Posts')]", By.XPATH),
                ("//li[contains(., 'Posts')]", By.XPATH),
                ("//div[contains(text(), 'Posts')]", By.XPATH),
                
                # CSS selectors
                (".search-reusables__filter-pill-button:contains('Posts')", By.CSS_SELECTOR),
                (".artdeco-pill:contains('Posts')", By.CSS_SELECTOR),
                (".search-reusables__filter-pill:contains('Posts')", By.CSS_SELECTOR),
                
                # Find by contents
                (".search-reusables__primary-filter button", By.CSS_SELECTOR),
                (".search-reusables__filter-pill-button", By.CSS_SELECTOR),
                (".artdeco-pill", By.CSS_SELECTOR)
            ]
            
            # Try each selector
            for selector, selector_type in post_filter_selectors:
                try:
                    logger.debug(f"Trying selector: {selector}")
                    
                    # For CSS selectors with :contains (which Selenium doesn't support),
                    # we need a different approach
                    if ":contains" in selector:
                        # Find all elements that match the base selector
                        base_selector = selector.split(":contains")[0]
                        search_text = selector.split("'")[1]
                        
                        elements = self.browser.driver.find_elements(By.CSS_SELECTOR, base_selector)
                        for element in elements:
                            if search_text in element.text:
                                if element.is_displayed() and element.is_enabled():
                                    self.browser.click_element(element)
                                    self.browser.human_wait()
                                    logger.info(f"Successfully clicked Posts filter with text matching: {search_text}")
                                    return True
                    else:
                        # Regular selector
                        posts_filter = self.browser.wait_for_element(selector, selector_type, timeout=3)
                        if posts_filter and posts_filter.is_displayed() and posts_filter.is_enabled():
                            self.browser.click_element(posts_filter)
                            self.browser.human_wait()
                            logger.info(f"Successfully clicked Posts filter with selector: {selector}")
                            return True
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # If we get here, we couldn't find the Posts filter
            # Try a different approach - look for elements that contain "Posts"
            try:
                all_elements = self.browser.driver.find_elements(By.XPATH, "//*[contains(text(), 'Post') or contains(text(), 'post')]")
                
                for element in all_elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            element_text = element.text
                            logger.info(f"Found potential filter element: '{element_text}'")
                            
                            if "post" in element_text.lower() and len(element_text) < 20:
                                self.browser.click_element(element)
                                self.browser.human_wait()
                                logger.info(f"Clicked on element with text: {element_text}")
                                return True
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Failed to find any elements containing 'Post': {e}")
            
            # If we still couldn't find it, we'll continue without filtering
            logger.warning("Could not find Posts filter. Continuing without filtering.")
            return False
            
        except Exception as e:
            logger.error(f"Filter failed: {e}")
            return False