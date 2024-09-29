from bs4 import BeautifulSoup
from selenium.common import TimeoutException, ElementNotInteractableException
from selenium.webdriver.support.wait import WebDriverWait

from src.model.category import Category
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def processed_last_page(index, soup):
    weiter_button =  soup.find('li', class_='l-Be8I')
    parent = weiter_button.parent
    # x = parent[len(parent)-2]
    return index-1 == int(parent.contents[len(parent)-2].text)




class Scraper:
    upper_limit_per_category = 150
    def __init__(self, base_url):
        self._base_url = base_url
        self.driver = self.create_driver()

    def create_driver(self):
        driver = webdriver.Firefox()
        return driver

    def get_dynamic_soup(self, url = None):
        if url:
            self.driver.get(url)
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    # def quit_driver(self, driver):
    #     driver.quit()
    def quit_driver(self):
        self.driver.quit()
    @property
    def base_url(self):
        return self._base_url

    def scrape(self):
        categories = self._get_categories()

        for category in categories:
            if category.url and category.name == "Ausverkauf":
                self._scrape_category(category)


    # GET ALL CATEGORIES AND ITS CORRESPONDING URLS
    def _get_categories(self):
        soup = self.get_dynamic_soup(self.base_url)
        navigation_bar = soup.findAll('nav')
        ul = navigation_bar[2].find('ul')
        categories = []
        for li in ul.find_all('li'):
            category_name = li.get_text(strip=True)
            if category_name == 'Übersicht' or category_name == 'Prospekt':
                continue
            category_url = li.find('a').get('href') if li.find('a') else None
            print("Getting info for category: ", category_name)
            category_instance = Category(category_name, category_url)
            categories.append(category_instance)
        return categories

    def _scrape_category(self, category):
        self.driver.get(self.base_url + category.url + '?page=1')
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # extract links from first page
        product_links = [a.get('href') for a in soup.find_all('a',class_='Q_opE0', href=True)]

        self._loop_through_pages_and_extract_links(category,product_links, soup)
        self._extract_data(product_links, category)


    def _loop_through_pages_and_extract_links(self, category, product_links, soup):
        has_next_page = soup.find(lambda tag: tag.name == 'span' and tag.get_text() == 'Weiter')
        index = 1
        while has_next_page and len(product_links) < self.upper_limit_per_category and not processed_last_page(index, soup):
            index += 1
            self.driver.get(self.base_url + category.url + '?page=' + str(index)) #'&sort=price-desc' not allowed according to robots.txt
            # Update the BeautifulSoup object
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Scrape the links from the page
            product_links.extend([a.get('href') for a in soup.find_all('a', class_='Q_opE0', href=True)])
            has_next_page = soup.find(lambda tag: tag.name == 'span' and tag.get_text() == 'Weiter')

    def _extract_data(self, product_links, category):
        extracted_data = []



        return extracted_data



