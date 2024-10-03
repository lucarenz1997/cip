import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.options import Options

from src.utils.log_executor_decorator import log_execution


# Scraper class for scraping articles from Interdiscount website.
class Scraper:
    _max_pages_to_scrape = 40  # each page has 24 articles
    _save_interval = 200  # Accumulate data into the dataframe every 100 articles

    def __init__(self, base_url):
        self._base_url = base_url
        self._driver = self._create_driver()
        self._article_data = []  # Temporary list to store article data
        self._df = pd.DataFrame(
            columns=["name", "price", "description", "category", "rating", "brand",
                     "source"])  # DataFrame to hold all data

    @log_execution
    def scrape(self):
        categories = self._get_categories()


    def _create_driver(self):
        profile = FirefoxProfile()
        profile.set_preference("permissions.default.image", 2)  # Disable images
        options = Options()
        options.profile = profile
        options.headless = True  # Enable headless mode
        driver = webdriver.Firefox(options=options)
        return driver

    def _quit_driver(self):
        self._driver.quit()
        print("Driver has been closed.")


    def _get_categories(self):
        soup = self._get_dynamic_soup(self._base_url)
        navigation_bar = soup.findAll('li', class_='sc-ba0f659-0')

        print("hoi")

    def _get_dynamic_soup(self, url=None):
        if url:
            self._driver.get(url)
        html = self._driver.page_source
        return BeautifulSoup(html, 'html.parser')