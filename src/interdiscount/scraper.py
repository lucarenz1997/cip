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
from urllib.parse import quote


# Scraper class for scraping articles from Interdiscount website.
class Scraper(BaseScraper):
    _max_pages_to_scrape = 40  # each page has 24 articles
    _save_interval = 200  # Accumulate data into the dataframe every 100 articles

    def __init__(self, base_url):
        super().__init__(base_url)
        self._interactive_mode = UIUtils.ask_interactive_mode() == 'yes'
        self._article_data = []  # Temporary list to store article data
        self._brands_df = pd.DataFrame(
            columns=["category", "brand_name", "article_count"]
        )
        self._article_df = pd.DataFrame(
            columns=["name", "price", "description", "category", "rating", "brand", "sub_category"])

    def scrape(self):
        print(f"Fetching categories from {self._base_url}")
        categories = self._get_categories()
        if self._interactive_mode:
            categories = UIUtils.show_selection_window_dropdown_3_levels(categories,
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
                        "sub_category": article.sub_category
                    })

                    # If we've collected 100 articles, append them to the dataframe
                    if len(self._article_data) >= self._save_interval:
                        print("writing into df")
                        self._article_df = pd.concat([self._article_df, pd.DataFrame(self._article_data)], ignore_index=True)
                        self._article_data.clear()  # Clear the list after appending

        # Append any remaining data to the dataframe at the end of scraping
        if self._article_data:
            self._article_df = pd.concat([self._article_df, pd.DataFrame(self._article_data)], ignore_index=True)

        # Save the dataframe to CSV at the end
        csv_file_path = self.save_to_csv(self._article_df, 'raw.csv')
        self._article_df.to_csv(csv_file_path, sep='|', index=False)

        self._quit_driver()
        print("SCRAPING DONE")
        return self._article_df

    @log_execution
    def _get_categories(self):
        soup = self._update_soup(self._base_url)
        navigation_bar = soup.findAll('nav')
        ul = navigation_bar[2].find('ul')
        categories = []
        for li in ul.find_all('li'):
            category_name = li.get_text(strip=True)
            # if category_name in ['Übersicht', 'Prospekt']:  # has no articles. hence, we ignore them
            if category_name not in ['TV & Audio']:  # if you only want to check the headphones example, comment the upper if statement and comment this one out (for time-reasons)
                continue
            category_url = li.find('a').get('href') if li.find('a') else None

            # we just want to go two levels further down. if you're brave enough, do the recursion and you can wait 30+ minutes to go through all categories and its sub-sub-sub....categories ;-)
            sub_cats = self._get_sub_categories(category_url)
            categories.append(Category(category_name, category_url, sub_cats))
        return categories

    @log_execution
    def _scrape_category(self, category):
        self._driver.get(self._base_url + category.url + '?page=1')
        all_brands = self._get_all_brands()

        # Get the deepest subcategory or category name
        subcategory_name = self._get_deepest_subcategory_name(category)

        selected_brands = UIUtils.show_selection_window(all_brands, "Select the brands that you want to scrape") \
            if self._interactive_mode else []
        # add all brands to dataframe: self._brands_df.
        self._update_brands_df(subcategory_name, all_brands)
        article_count = 0
        for article_link in self._extract_all_product_links_in_category(category, selected_brands):

            yield self._extract_data(article_link, category, self._get_brand(article_link, selected_brands))
            article_count += 1
            if article_count % 300 == 0: # in case you want to scrape the entire interdiscount, we make sure your application does not crash due to memory issues.
                self._release_memory()

    def _get_deepest_subcategory_name(self, category):
        """Recursively get the name of the deepest subcategory or the category name itself."""
        # Traverse subcategories until you reach the last one
        current_category = category
        while current_category.subcategory:
            # Move to the last subcategory in the list
            current_category = current_category.subcategory[-1]

        return current_category.name

    def _update_brands_df(self, category_name, brands):
        """Update the brands DataFrame with the latest brand names and article counts."""

        # Create a list of dictionaries for each brand's name and article count
        brand_data = [
            {
                "category": category_name,  # Same category for all
                "brand_name": brand.name,  # Use brand.name attribute
                "article_count": brand.article_count  # Use brand.article_count attribute
            }
            for brand in brands  # Loop through the brands array
        ]

        # Append the data to the DataFrame
        self._brands_df = pd.concat([self._brands_df, pd.DataFrame(brand_data)], ignore_index=True)

        # Write the DataFrame to a CSV file after processing each category
        self._brands_df.to_csv("data\\brands.csv", index=False)

        print(f"Data for {category_name} saved to brands.csv")

    @log_execution
    def _get_all_brands(self):
        self._wait_until_element_located(By.XPATH, "//button[.//span[text()='Marken']]",
                                         'click')  # Open brands dropdown
        soup = self._update_soup(sleep_timer=0.2)
        all_brands_list = soup.findAll("fieldset")[0].contents[2]

        brands = []
        for brand_element in all_brands_list.findAll('div')[::3]:  # we have always 3 divs per entry

            match = re.match(r'(.*?)\s*\((\d+)\)', brand_element.text)  # Brand (# of articles)
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
        return InterdiscountArticle(name, price, description, category, rating, brand, exact_category)

    def _get_price(self, soup):
        price = soup.find('span', attrs={'data-testid': 'product-price'})
        return float(price.contents[0].text.replace(".–", '').replace("’", ""))

    def _get_description(self, soup):
        self._wait_until_element_located(By.ID, "collapsible-description", 'click')
        description = soup.find('div', attrs={'data-testid': 'text-clamp'}).contents[0].text.replace("\n", " ")
        return description.strip('"') if description else None

    def _get_rating(self):

        if not self._wait_until_element_located(By.XPATH, "//button[text()='Bewertungen']"):
            return None # articles to be reserved do not have this
        try:
            self._wait_until_element_located(By.ID, "collapsible-reviews", 'click')  # open Reviews/Bewertungen
        except Exception as e:
            print("collapsible reviews does not exist")

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
                rating = float(rating_div.contents[0].text)
            else:  # there are reviews
                rating = float(review_controls.find('div', class_='mr-4').text)
        except Exception:
            # other way of not having any reviews (interdiscount has multiple ways to display this)
            rating = None
        return rating

    def _extract_all_product_links_in_category(self, category, brands):
        brands_url = ""
        if brands:
            brands_url = "&brand=" + "+".join(
                [quote(brand.name, encoding='UTF-8') for brand in brands])  # brand names with "," etc do not work, sorry

        index = 1
        contains_clickable_weiter_button = True
        while index <= self._max_pages_to_scrape and contains_clickable_weiter_button:
            index += 1
            url = self._base_url + category.url + f'?page={index}{brands_url}'
            soup = self._update_soup(url=url, sleep_timer=0.4)
            contains_clickable_weiter_button = soup.select('a:-soup-contains("Weiter")')
            yield from self._get_article_links(soup)

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

    def _get_sub_categories(self, category_url, index = 0):
        soup = self._update_soup(self._base_url + category_url, 0.3)
        subcategories = []
        for subcategory in soup.select('nav > ul',
                                       class_="divide-y divide-gray-200 overflow-hidden border-y border-y-gray-200 leading-7 text-gray-700")[
                               2].select('li > a')[2+index::]: # we only want its sub categories. so the index increases per subcategory
            subcat_url = subcategory.get('href')
            subcat_name = subcategory.text
            if index == 0:
                sub_sub_cat = self._get_sub_categories(subcat_url, index=index+1)
            else:
                sub_sub_cat = None

            subcategories.append(Category(subcat_name, subcat_url, sub_sub_cat))
        return subcategories
