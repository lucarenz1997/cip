import re
import time

import pandas as pd
import unicodedata
from selenium.webdriver.common.by import By

from src.interdiscount.model.interdiscount_article import InterdiscountArticle
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
        self._df = pd.DataFrame(
            columns=["name", "price", "description", "category", "rating", "brand",
                     "source", "sub_category"])

    def scrape(self):
        soup = self._update_soup(self._base_url)
        categories = self._get_categories(soup)
        if self._interactive_mode:
            categories = UIUtils.show_selection_window_dropdown(categories,
                                                                "Select the categories that you want to scrape")

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
                        "source": article.source,
                        "sub_category": article.sub_category
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
        print("SCRAPING DONE")
        return self._df

    @log_execution
    def _get_categories(self, soup):
        navigation_bar = soup.findAll('nav')
        ul = navigation_bar[2].find('ul')
        categories = []
        for li in ul.find_all('li'):
            category_name = li.get_text(strip=True)
            if category_name in ['Übersicht', 'Prospekt']:  # has no articles. hence, we ignore them
                continue
            category_url = li.find('a').get('href') if li.find('a') else None

            # we just want to go one level further down. if you're brave enough, do the recursion and you can wait 30 minutesto go through all categories ;-)
            sub_cats = self._get_sub_categories(category_url)
            categories.append(Category(category_name, category_url, sub_cats))
        return categories

    @log_execution
    def _scrape_category(self, category):
        self._driver.get(self._base_url + category.url + '?page=1')
        brands = UIUtils.show_selection_window(self._get_all_brands(), "Select the brands that you want to scrape") \
            if self._interactive_mode else []

        article_count = 0
        for article_link in self._extract_all_product_links_in_category(category, brands):

            yield self._extract_data(article_link, category, self._get_brand(article_link, brands))
            article_count += 1
            if article_count % 300 == 0:
                self._release_memory()

    @log_execution
    def _get_all_brands(self):
        self._wait_until_element_located(By.XPATH, "//button[.//span[text()='Marken']]",
                                         'click')  # Open brands dropdown
        soup = self._update_soup(sleep_timer=0.2)
        all_brands_list = soup.findAll("fieldset")[0].contents[2]

        brands = []
        for brand_element in all_brands_list.findAll('div')[::3]:  # we have always 3 divs per entry

            match = re.match(r'(.*?)\s*\((\d+)\)', brand_element.text)  # Brand (# of articles))
            if match:
                brand_name = match.group(1).strip()
                article_count = int(match.group(2))
                brands.append(Brand(brand_name, article_count))

        return brands

    def _close_cookie_banner(self):
        try:
            self._driver.find_element(By.CLASS_NAME, 'h-min').click()
        except Exception:
            print("Cookie banner not found")

    def _extract_data(self, article_link, category, brand):
        soup = self._update_soup(self._base_url + article_link)

        price = self._get_price(soup)
        name = soup.find('h1').contents[0].text.strip('"')
        description = self._get_description(soup)
        rating = self._get_rating()
        exact_category = soup.select('nav ol > li')[-2].text
        return InterdiscountArticle(name, price, description, category, rating, brand, "interdiscount", exact_category)

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
        except Exception as e:
            print("collapsible reviews not found")

        try:
            soup = self._update_soup(sleep_timer=0.3)
            review_controls = soup.find(id='collapsible-reviews-controls')
            review_text = review_controls.text
            if "Es liegen noch keine Bewertungen vor" in review_text:
                rating = None
            elif "Es liegen nur wenige" in review_text:
                first_child = review_controls.find_all(recursive=False)[0].find_all(recursive=False)[0]

                # Find the third <div> inside the first child
                rating_div = first_child.find_all('div')[2]
                # Extract the text and convert to float
                rating = float(rating_div.contents[0].text)
            else:  # there are reviews
                rating = float(review_controls.find('div', class_='mr-4').text)
        except Exception:
            print("Rating could not be extracted")
            rating = None
        return rating

    def _extract_all_product_links_in_category(self, category, brands):
        brands_url = ""
        if brands:
            brands_url = "&brand=" + "+".join(
                [brand.name.replace(" ", "%2520") for brand in brands])  # brand names with "," etc do not work, sorry

        index = 1
        contains_clickable_weiter_button = True
        while index <= self._max_pages_to_scrape and contains_clickable_weiter_button:
            index += 1
            url = self._base_url + category.url + f'?page={index}{brands_url}'
            soup = self._update_soup(url=url, sleep_timer=0.4)
            yield from self._get_article_links(soup)
            contains_clickable_weiter_button = soup.select('a:-soup-contains("Weiter")')

    def _get_article_links(self, soup):
        time.sleep(0.3)
        # Select the <ul> with the 'data-testid="category-wrapper"' attribute
        ul = soup.select_one('ul[data-testid="category-wrapper"]')

        if ul:
            # Find all <li> > <article> > <a> inside the <ul> and extract the href attributes
            links = ul.select('li > article > a')

            for link in links:
                yield link.get('href')
        else:
            print("No <ul> with data-testid='category-wrapper' found.")

    def _get_brand(self, article_link, brands):
        article_link = unicodedata.normalize('NFKD', article_link.split("/")[3]).encode('ascii', 'ignore').decode(
            'utf-8').replace(" ", "-")  # get rid of umlaut, etc.

        for brand in brands:
            if str(article_link).startswith(brand.name.lower().replace(" ", "-")):
                return brand.name
        return None

    def _get_sub_categories(self, category_url):
        soup = self._update_soup(self._base_url + category_url, 0.3)
        subcategories = []
        for subcategory in soup.select('nav > ul',
                                       class_="divide-y divide-gray-200 overflow-hidden border-y border-y-gray-200 leading-7 text-gray-700")[
                               2].select('li > a')[2::]:
            subcat_url = subcategory.get('href')
            subcat_name = subcategory.text
            subcategories.append(Category(subcat_name, subcat_url, None))
        return subcategories
