import csv
import os

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.model.article import Article
from src.model.category import Category
from src.utils.log_executor_decorator import log_execution


class Scraper:
    upper_limit_per_category = 20
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

    def quit_driver(self):
        self.driver.quit()
        print("driver quit")

    def processed_last_page(index, soup):
        weiter_button = soup.find('li', class_='l-Be8I')
        parent = weiter_button.parent
        return index - 1 == int(parent.contents[len(parent) - 2].text)
    @property
    def base_url(self):
        return self._base_url

    def scrape(self):
        categories = self._get_categories()
        self._close_cookie_banner()

        data_dir = os.path.join(os.getcwd(), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        csv_file_path = os.path.join(data_dir, 'results.csv')
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Name", "Price", "Description", "Category", "Rating", "Source"])  # Write the header
            for category in categories:
                if category.url:
                    # get all urls for articles in category
                    self._scrape_category(category, writer)
                        # self.write_to_csv(writer, article)

        # result = []
        # for category in categories:
        #     if category.url:
        #         #get all urls for articles in category
        #         result.append(self._scrape_category(category))
        # self.write_to_csv(result)
        self.quit_driver()

    def write_to_csv(self, writer, article):
        writer.writerow([article.name, article.price, article.description, article.category.name,
                         article.rating, article.source])
        # data_dir = os.path.join(os.getcwd(), 'data')
        # if not os.path.exists(data_dir):
        #     os.makedirs(data_dir)
        # csv_file_path = os.path.join(data_dir, 'results.csv')
        # # Write the results to a CSV file
        # with open(csv_file_path, 'w', newline='',encoding='utf-8') as file:
        #     writer = csv.writer(file)
        #     writer.writerow(
        #         ["Name", "Price", "Description", "Category", "Rating", "Source"])  # Write the header
        #     for articles in result:
        #         for article in articles:
        #             writer.writerow([article.name, article.price, article.description, article.category.name,
        #                              article.rating, article.source])

    # GET ALL CATEGORIES AND ITS CORRESPONDING URLS
    @log_execution
    def _get_categories(self):
        soup = self.get_dynamic_soup(self.base_url)
        navigation_bar = soup.findAll('nav')
        ul = navigation_bar[2].find('ul')
        categories = []
        for li in ul.find_all('li'):
            category_name = li.get_text(strip=True)
            if category_name == 'Übersicht' or category_name == 'Prospekt':
                continue
            # if category_name != 'Ausverkauf':
            #     continue
            category_url = li.find('a').get('href') if li.find('a') else None
            category_instance = Category(category_name, category_url)
            categories.append(category_instance)
        return categories

    @log_execution
    def _scrape_category(self, category, writer):
        self.driver.get(self.base_url + category.url + '?page=1')
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # extract links from first page
        article_links = [a.get('href') for a in soup.find_all('a',class_='Q_opE0', href=True)]

        self._extract_all_product_links_in_category(category, article_links, soup)

        for article_link in article_links:
            self.write_to_csv(writer, self._extract_data(article_link, category))


    @log_execution
    def _extract_all_product_links_in_category(self, category, article_links, soup):
        has_next_page = soup.find(lambda tag: tag.name == 'span' and tag.get_text() == 'Weiter')
        index = 1
        while has_next_page and len(article_links) < self.upper_limit_per_category and not self.processed_last_page(index, soup):
            index += 1
            self.driver.get(self.base_url + category.url + '?page=' + str(index)) #'&sort=price-desc' not allowed according to robots.txt
            # Update the BeautifulSoup object
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Scrape the links from the page
            article_links.extend([a.get('href') for a in soup.find_all('a', class_='Q_opE0', href=True)])
            has_next_page = soup.find(lambda tag: tag.name == 'span' and tag.get_text() == 'Weiter')

    def _extract_data(self, article_link, category):
        soup = self._setup_soup(article_link)
        price = self._get_price(soup)
        name = soup.find('h1').contents[0].text
        description = self._get_description(soup)
        rating = self._get_rating(soup)
        article_link = Article(name, price, description, category, rating, "interdiscount")
        return article_link

    def _setup_soup(self, article_link):
        self.driver.get(self.base_url + article_link)
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    def _get_price(self, soup):
        price = soup.find('span', attrs={'data-testid': 'product-price'})
        price = float(price.contents[0].text.replace(".–", '').replace("’", ""))
        return price

    def _get_rating(self, soup):
        # articles to be reserved do not have this
        if not soup.find("button", text="Bewertungen"):
            return None
        try:
            self.wait_until_element_located(By.ID, "collapsible-reviews", 'click')  # open Reviews/Bewertungen
            self.wait_until_element_located(By.ID, "collapsible-reviews-controls")
        except Exception as e:
            print("collapsible reviews not found")
        try:
            review_text = self.wait_until_element_located(By.XPATH, f"//*[@id='collapsible-reviews-controls']",'text')
            if "Es liegen noch keine Bewertungen vor" in review_text:
                rating = None
            elif "Es liegen nur wenige" in review_text:
                rating_div = self.wait_until_element_located(By.XPATH,
                                                             f"//*[@id='collapsible-reviews-controls']/*[1]/*[1]")
                rating = float(rating_div.find_element(by=By.XPATH, value=".//div[3]").text)
                # TODO get number of reviews
            else:  # there are reviews
                rating = float(self.wait_until_element_located(By.XPATH,
                                                               "//div[contains(text(), 'Gesamtbewertung')]").parent.find_element(
                    by=By.XPATH, value=f"./*[1]").find_element(by=By.CLASS_NAME,
                                                               value="mr-4").text)
                # TODO get number of reviews
        except Exception as e:
            print("Error caught: ", e)
            rating = None
        return rating

    def _get_description(self, soup):
        self.wait_until_element_located(By.ID, "collapsible-description", action='click')
        description = soup.find('div', attrs={'data-testid': 'text-clamp'}).contents[0].text
        description = description if description and description.strip() else None
        return description

    def _close_cookie_banner(self):
        try:
            self.driver.find_element(by=By.CLASS_NAME,
                                     value='h-min').click()  # close cookie-banner
        except Exception as e:
            print("Cookie banner not found")

    def wait_until_element_located(self, by, value, action=None):
        try:

            wait = WebDriverWait(self.driver, 3)
            element = wait.until(EC.presence_of_element_located((by, value)))
        # Use JavaScript to scroll the element into view but with some offset to avoid the fixed header
            self.driver.execute_script("arguments[0].scrollIntoView();", element)
            # Adjust the scroll by a fixed number of pixels down to account for the header
            self.driver.execute_script("window.scrollBy(0, -150);")  # Adjust -150 to the height of your fixed header

            if action == 'click':
                element.click()
            elif action == 'text':
                return element.text
            return element
        except Exception as e:
            print("Element does not exist", e)


