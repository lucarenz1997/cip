import re
import time

import pandas as pd
import unicodedata
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.options import Options

from src.model.article import Article
from src.model.base_scraper import BaseScraper
from src.model.brand import Brand
from src.model.category import Category
from src.utils.log_executor_decorator import log_execution
from src.utils.ui_utils import UIUtils


# Scraper class for scraping articles from Interdiscount website.
class Scraper(BaseScraper):
    _max_pages_to_scrape = 40  # each page has 24 articles
    _save_interval = 200  # Accumulate data into the dataframe every 100 articles

    def __init__(self, base_url):
        super().__init__(base_url)
        self._interactive_mode = UIUtils.ask_interactive_mode() == 'yes'
        self._article_data = []  # Temporary list to store article data

    @log_execution
    def scrape(self):
        categories = self._get_categories()
        if self._interactive_mode:
            categories = self._select_categories(categories)

        self._close_cookie_banner()

        # Iterate over selected categories and scrape articles
        for category in categories:
            if category.url:
                for article in self._scrape_category(category):
                    # Add each article to the temporary list
                    self._article_data.append({
                        "name": article.name,
                        "price": article.price,
                        "description": article.description,
                        "category": article.category.name,
                        "rating": article.rating,
                        "brand": article.brand,
                        "source": article.source
                    })

                    # If we've collected 100 articles, append them to the dataframe
                    if len(self._article_data) >= self._save_interval:
                        print("writing into df")
                        self._df = pd.concat([self._df, pd.DataFrame(self._article_data)], ignore_index=True)
                        self._article_data.clear()  # Clear the list after appending

        # Append any remaining data to the dataframe at the end of scraping
        if self._article_data:
            self._df = pd.concat([self._df, pd.DataFrame(self._article_data)], ignore_index=True)

        # Save the dataframe to CSV at the end
        csv_file_path = self.save_to_csv(self._df, 'raw.csv')
        self._df.to_csv(csv_file_path, sep='|', index=False)

        self._quit_driver()
        return self._df

    def _create_driver(self):
        profile = FirefoxProfile()
        profile.set_preference("permissions.default.image", 2)  # Disable images
        options = Options()
        options.profile = profile
        options.headless = True  # Enable headless mode
        driver = webdriver.Firefox(options=options)
        return driver

    def _get_categories(self):
        soup = self._get_dynamic_soup(self._base_url)
        navigation_bar = soup.findAll('nav')
        ul = navigation_bar[2].find('ul')
        categories = []
        for li in ul.find_all('li'):
            category_name = li.get_text(strip=True)
            if category_name in ['Übersicht', 'Prospekt']:  # has no articles. hence, we ignore them
                continue
            category_url = li.find('a').get('href') if li.find('a') else None
            categories.append(Category(category_name, category_url))
        return categories

    def _scrape_category(self, category):
        self._driver.get(self._base_url + category.url + '?page=1')
        soup = BeautifulSoup(self._driver.page_source, 'html.parser')

        brands = self._select_brands(self._get_all_brands()) if self._interactive_mode else []

        article_count = 0
        for article_link in self._extract_all_product_links_in_category(category, soup, brands):

            yield self._extract_data(article_link, category, self._get_brand(article_link, brands))
            article_count += 1
            if article_count % 300 == 0:
                self._release_memory()

    def _get_all_brands(self):
        self._wait_until_element_located(By.XPATH, "//button[.//span[text()='Marken']]",
                                         'click')  # Open brands dropdown

        # Find all the options within the listbox
        parent_div = self._wait_until_element_located(
            By.XPATH, "//div[@aria-label='Optionen wählen']", 'get')

        # Iterate through each option to get the name and number
        # Find all child divs within the parent div
        option_divs = parent_div.find_elements(By.XPATH, ".//div[@role='option']")

        # Iterate over each child div and extract the name and number
        brands = []
        for option in option_divs:
            try:
                name = option.find_element(By.XPATH,
                                           ".//span[@class='cursor-pointer select-none pl-2 text-base text-brand-secondary']").text.strip()

                match = re.match(r'(.*?)\s*\((\d+)\)', name)
                if match:
                    brand_name = match.group(1).strip()
                    article_count = int(match.group(2))
                    brands.append(Brand(brand_name, article_count))
            except Exception as e:
                print(f"Error extracting data: {e}")

        return brands

    def _select_brands(self, brands):
        return UIUtils.show_selection_window(brands, "Select the brands that you want to scrape")

    def _select_categories(self, categories):
        return UIUtils.show_selection_window(categories, "Select the categories that you want to scrape")

    def _close_cookie_banner(self):
        try:
            self._driver.find_element(By.CLASS_NAME, 'h-min').click()
        except Exception as e:
            print("Cookie banner not found")

    def _extract_data(self, article_link, category, brand):
        soup = self._setup_soup(article_link)
        price = self._get_price(soup)
        name = soup.find('h1').contents[0].text.strip('"')
        description = self._get_description(soup)
        rating = self._get_rating()
        return Article(name, price, description, category, rating, brand, "interdiscount")

    def _setup_soup(self, article_link):
        self._driver.get(self._base_url + article_link)
        html = self._driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    def _get_dynamic_soup(self, url=None):
        if url:
            self._driver.get(url)
        html = self._driver.page_source
        return BeautifulSoup(html, 'html.parser')

    def _get_price(self, soup):
        price = soup.find('span', attrs={'data-testid': 'product-price'})
        return float(price.contents[0].text.replace(".–", '').replace("’", ""))

    def _get_description(self, soup):
        self._wait_until_element_located(By.ID, "collapsible-description", 'click')
        description = soup.find('div', attrs={'data-testid': 'text-clamp'}).contents[0].text.replace("\n", " ")
        return description.strip('"') if description else None

    def _get_rating(self):
        # articles to be reserved do not have this
        if not self._wait_until_element_located(By.XPATH, "//button[text()='Bewertungen']"):
            return None
        try:
            self._wait_until_element_located(By.ID, "collapsible-reviews", 'click')  # open Reviews/Bewertungen
            self._wait_until_element_located(By.ID, "collapsible-reviews-controls")
        except Exception as e:
            print("collapsible reviews not found")

        try:
            time.sleep(0.1)
            review_text = self._wait_until_element_located(By.XPATH, f"//*[@id='collapsible-reviews-controls']", 'text')
            if "Es liegen noch keine Bewertungen vor" in review_text:
                rating = None
            elif "Es liegen nur wenige" in review_text:
                rating_div = self._wait_until_element_located(By.XPATH,
                                                              f"//*[@id='collapsible-reviews-controls']/*[1]/*[1]")
                rating = float(rating_div.find_element(by=By.XPATH, value=".//div[3]").text)
            else:  # there are reviews
                rating = float(self._wait_until_element_located(By.XPATH,
                                                                "//div[contains(text(), 'Gesamtbewertung')]").parent.find_element(
                    by=By.XPATH, value=f"./*[1]").find_element(by=By.CLASS_NAME,
                                                               value="mr-4").text)
        except Exception as e:
            print("Error caught: ", e)
            rating = None
        return rating

    def _extract_all_product_links_in_category(self, category, soup, brands):
        has_next_page = soup.findAll('svg', class_="iconVariantB")
        index = 0
        brands_url = ""
        if brands:
            brands_url = "&brand=" + "+".join([re.sub(r"[' ]", "%20", brand.name) for brand in brands])

        while has_next_page and index < self._max_pages_to_scrape and not self._processed_last_page(index, soup):
            index += 1
            url = self._base_url + category.url + f'?page={index}{brands_url}'
            self._driver.get(url)
            soup = BeautifulSoup(self._driver.page_source, 'html.parser')

            for a in soup.find_all('a', class_='Q_opE0', href=True):
                yield a.get('href')
            has_next_page = soup.find(lambda tag: tag.name == 'span' and tag.get_text() == 'Weiter')

    def _processed_last_page(self, index, soup):
        weiter_button = soup.find('li', class_='l-Be8I')  # fixed after update "
        parent = weiter_button.parent
        return index - 1 == int(parent.contents[len(parent) - 2].text)

    def _get_brand(self, article_link, brands):
        article_link = unicodedata.normalize('NFKD', article_link.split("/")[3]).encode('ascii', 'ignore').decode(
            'utf-8').replace(" ", "-")  # get rid of umlaut, etc.

        for brand in brands:
            if str(article_link).startswith(brand.name.lower().replace(" ", "-")):
                return brand.name
        return None
