import csv
import os

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.model.article import Article
from src.model.category import Category


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

    # def quit_driver(self, driver):
    #     driver.quit()
    def quit_driver(self):
        self.driver.quit()

    def processed_last_page(index, soup):
        weiter_button = soup.find('li', class_='l-Be8I')
        parent = weiter_button.parent
        return index - 1 == int(parent.contents[len(parent) - 2].text)
    @property
    def base_url(self):
        return self._base_url

    def scrape(self):
        categories = self._get_categories()

        result = []
        for category in categories:
            if category.url:
                result.append(self._scrape_category(category))

        self.write_to_csv(result)
        self.quit_driver()

    def write_to_csv(self, result):
        data_dir = os.path.join(os.getcwd(), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        csv_file_path = os.path.join(data_dir, 'results.csv')
        # Write the results to a CSV file
        with open(csv_file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Name", "Price", "Description", "Category", "Rating", "Source"])  # Write the header
            for articles in result:
                for article in articles:
                    writer.writerow([article.name, article.price, article.description, article.category.name,
                                     article.rating, article.source])

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
            # if category_name != 'Ausverkauf' or category_name != 'Ballsport':
            #     continue
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
        article_links = [a.get('href') for a in soup.find_all('a',class_='Q_opE0', href=True)]

        self._loop_through_pages_and_extract_links(category,article_links, soup)

        articles = []
        for article_link in article_links:
            articles.append(self._extract_data(article_link, category))
        return articles



    def _loop_through_pages_and_extract_links(self, category, article_links, soup):
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
        self.driver.get(self.base_url + article_link)
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        price = soup.find('span', attrs={'data-testid': 'product-price'})
        price = float(price.contents[0].text.replace(".–",'').replace("’", ""))
        name = soup.find('h1').contents[0].text
        try:
            self.driver.find_element(by=By.CLASS_NAME, value='h-min').click()  # close cookie-banner # TODO do this only once?!
        except Exception as e:
            print("cookie not found")

        self.wait_until_element_located(By.ID, "collapsible-description").click()
        # element.click()  # open Description/Beschreibung
        description = soup.find('div', attrs={'data-testid': 'text-clamp'}).contents[0].text
        description = description if description and description.strip() else None
        try:
            self.wait_until_element_located(By.ID, "collapsible-reviews").click()
            self.wait_until_element_located(By.ID, "collapsible-reviews-controls").click()

            # open Reviews/Bewertungen
        except Exception as e:
            print("collapsible reviews not found")

        try :
            review_text = self.wait_until_element_located(By.XPATH, f"//*[@id='collapsible-reviews-controls']").text

            if "Es liegen noch keine " in review_text:
                rating = None
            elif "Es liegen nur wenige" in review_text:
                rating_div = self.driver.find_element(by=By.XPATH, value=f"//*[@id='collapsible-reviews-controls']/*[1]/*[1]")
                rating = float(rating_div.find_element(by=By.XPATH, value=".//div[3]").text)
            else: # there are reviews
                rating =float(self.wait_until_element_located(By.XPATH, "//div[contains(text(), 'Gesamtbewertung')]").parent.find_element(by=By.XPATH, value=f"./*[1]").find_element(by=By.CLASS_NAME,
                                                                                                      value="mr-4").text)

        except Exception as e:
            print("issue with reviewers: ",e )
            rating = None
        article_link = Article(name, price, description, category, rating, "interdiscount")
        return article_link

    def wait_until_element_located(self, by, value, timeout=10):
        wait = WebDriverWait(self.driver, timeout)
        element = wait.until(EC.presence_of_element_located((by, value)))
        # Use JavaScript to scroll the element into view but with some offset to avoid the fixed header
        self.driver.execute_script("arguments[0].scrollIntoView();", element)
        # time.sleep(0.5)  # wait for half a second
        # Adjust the scroll by a fixed number of pixels down to account for the header
        self.driver.execute_script("window.scrollBy(0, -150);")  # Adjust -150 to the height of your fixed header

        return element


