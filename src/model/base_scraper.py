import gc
import os
import time
from abc import ABC, abstractmethod

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.web_driver_factory import WebDriverFactory


class BaseScraper(ABC):
    def __init__(self, base_url):
        self._base_url = base_url
        self._driver = WebDriverFactory.create_driver()

    @abstractmethod
    def scrape(self):
        """
        Abstract method that must be implemented by all classes that inherit from BaseScraper.
        """
        pass

    def _wait_until_element_located(self, by, value, action=None, sleep_time=0):
        try:
            wait = WebDriverWait(self._driver, 3)
            element = wait.until(EC.presence_of_element_located((by, value)))

            self._driver.execute_script("arguments[0].scrollIntoView();", element)
            time.sleep(sleep_time)
            self._driver.execute_script("window.scrollBy(0, -150);")
            time.sleep(sleep_time)

            if action == 'click':
                element.click()
            elif action == 'text':
                return element.text
            elif action == 'get':
                return element
            return element
        except Exception as e:
            return None

    def _release_memory(self):
        self._quit_driver()
        self._driver = WebDriverFactory.create_driver()
        gc.collect()

    def _quit_driver(self):
        self._driver.quit()
        print("Driver has been closed.")

    def save_to_csv(self, df, file_name, separator='|', index=False):
        data_dir = os.path.join(os.getcwd(), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        file_path = os.path.join(data_dir, file_name)
        df.to_csv(file_path, sep=separator, index=index)
        return file_path

    def _update_soup(self, url=None, sleep_timer=None):
        """
        Fetches the page source from the given URL and returns the BeautifulSoup object.

        :param url: The URL to fetch the page from.
        :param sleep_timer: Optional sleep time before fetching the page source (default is None).
        :return: BeautifulSoup object parsed from the fetched page.
        """
        if url:
            self._driver.get(url)

        if sleep_timer is not None:
            time.sleep(sleep_timer)

        html = self._driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

