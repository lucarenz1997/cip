import csv
import os
import gc
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import tkinter as tk
from tkinter import messagebox
import re
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

from src.interdiscount.Brand import Brand
from src.model.article import Article
from src.model.category import Category


# Scraper class for scraping articles from Interdiscount website.
class Scraper:
    # Initialize batch size and max pages to scrape
    _batch_size = 300
    _max_pages_to_scrape = 40 # each page has 24 articles

    # Constructor to set base URL and initiate the WebDriver
    def __init__(self, base_url):
        self._base_url = base_url
        self._driver = self._create_driver()
        self._interactive_mode = self._ask_interactive_mode() == 'yes'

    # Public method to start scraping
    def scrape(self):
        # Retrieve and optionally select categories
        categories = self._get_categories()
        if self._interactive_mode:
            categories = self._select_categories(categories)

        self._close_cookie_banner()  # Close cookie banner if present
        csv_file_path = self._create_data_directory_and_csv()

        with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = self._write_csv_header(file)
            # Iterate over selected categories and scrape articles
            for category in categories:
                if category.url:
                    for article in self._scrape_category(category):
                        writer.writerow([article.name, article.price, article.description,
                                         article.category.name, article.rating, article.source])

        self._quit_driver()  # Close the WebDriver

    # Private method to create and initialize the WebDriver
    def _create_driver(self):
        profile = FirefoxProfile()
        profile.set_preference("permissions.default.image", 2)  # Disable images
        options = Options()
        options.profile = profile
        options.headless = True  # Enable headless mode
        driver = webdriver.Firefox(options=options)
        return driver

    # Private method to gracefully close the WebDriver
    def _quit_driver(self):
        self._driver.quit()
        print("Driver has been closed.")

    # Private method to check if interactive mode is enabled
    def _ask_interactive_mode(self):
        root = tk.Tk()
        root.withdraw()
        result = messagebox.askquestion("Interactive Mode", "Do you want to scrape in interactive mode?",
                                        icon='warning')
        root.destroy()
        return result

    # Private method to get categories from the base URL
    def _get_categories(self):
        soup = self._get_dynamic_soup(self._base_url)
        navigation_bar = soup.findAll('nav')
        ul = navigation_bar[2].find('ul')
        categories = []
        for li in ul.find_all('li'):
            category_name = li.get_text(strip=True)
            if category_name in ['Übersicht', 'Prospekt']:
                continue
            category_url = li.find('a').get('href') if li.find('a') else None
            categories.append(Category(category_name, category_url))
        return categories

    # Private method to scrape articles per category
    def _scrape_category(self, category):
        self._driver.get(self._base_url + category.url + '?page=1')
        soup = BeautifulSoup(self._driver.page_source, 'html.parser')

        brands = self._select_brands(self._get_all_brands()) if self._interactive_mode else []

        article_count = 0
        for article_link in self._extract_all_product_links_in_category(category, soup, brands):
            yield self._extract_data(article_link, category)
            article_count += 1
            if article_count % self._batch_size == 0:
                self._release_memory()

    # Private method to handle memory release and browser restart
    def _release_memory(self):
        self._quit_driver()
        self._driver = self._create_driver()
        gc.collect()

    # Private method to get all brands available in the category
    def _get_all_brands(self):
        self._wait_until_element_located(By.CLASS_NAME, '_2HIFC0', 'click')  # Open brands dropdown
        div_with_all_brands = self._wait_until_element_located(By.CLASS_NAME, '_1o-3dE', 'get')  # Get brands container
        all_labels = div_with_all_brands.find_elements(By.TAG_NAME, value='label')
        brands = []
        for label in all_labels:
            match = re.match(r'(.*?)\s*\((\d+)\)', label.text)
            if match:
                brand_name = match.group(1).strip()
                article_count = int(match.group(2))
                brands.append(Brand(brand_name, article_count))
        return brands

    # Private method to handle the user selection of brands
    def _select_brands(self, brands):
        return self._show_selection_window(brands, "Select the brands that you want to scrape")

    # Private method to handle the user selection of categories
    def _select_categories(self, categories):
        return self._show_selection_window(categories, "Select the categories that you want to scrape")

    # Private method to display a selection window for brands/categories
    def _show_selection_window(self, objects, title):
        selected_objects = []

        def on_ok():
            nonlocal selected_objects
            selected_indices = listbox.curselection()
            selected_objects = [objects[i] for i in selected_indices]
            root.destroy()

        root = tk.Tk()
        root.title(title)
        window_height = int(root.winfo_screenheight() * 0.4)
        root.geometry(f"400x{window_height}")

        frame = tk.Frame(root)
        frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=window_height // 20, yscrollcommand=scrollbar.set)
        for obj in objects:
            listbox.insert(tk.END, f"{obj.name} ({obj.article_count})" if hasattr(obj, 'article_count') else obj.name)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=listbox.yview)

        ok_button = tk.Button(root, text="OK", command=on_ok)
        ok_button.pack(pady=10)

        root.mainloop()
        return selected_objects

    # Private method to close the cookie banner if it exists
    def _close_cookie_banner(self):
        try:
            self._driver.find_element(By.CLASS_NAME, 'h-min').click()
        except Exception as e:
            print("Cookie banner not found")

    # Private method to extract data from a product page
    def _extract_data(self, article_link, category):
        soup = self._setup_soup(article_link)
        price = self._get_price(soup)
        name = soup.find('h1').contents[0].text
        description = self._get_description(soup)
        rating = self._get_rating(soup)
        return Article(name, price, description, category, rating, "interdiscount")

    def _setup_soup(self, article_link):
        self._driver.get(self._base_url + article_link)
        html = self._driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup
    # Private method to create dynamic soup for a page
    def _get_dynamic_soup(self, url=None):
        if url:
            self._driver.get(url)
        html = self._driver.page_source
        return BeautifulSoup(html, 'html.parser')

    # Private method to extract price from a product page
    def _get_price(self, soup):
        price = soup.find('span', attrs={'data-testid': 'product-price'})
        return float(price.contents[0].text.replace(".–", '').replace("’", ""))

    # Private method to extract description from a product page
    def _get_description(self, soup):
        self._wait_until_element_located(By.ID, "collapsible-description", 'click')
        description = soup.find('div', attrs={'data-testid': 'text-clamp'}).contents[0].text.replace("\n", " ")
        return description.strip() if description else None

    # Private method to extract rating from a product page
    def _get_rating(self, soup):
        if not soup.find("button", text="Bewertungen"):
            return None
        try:
            self._wait_until_element_located(By.ID, "collapsible-reviews", 'click')
            review_text = self._wait_until_element_located(By.XPATH, "//*[@id='collapsible-reviews-controls']", 'text')
            if "Es liegen noch keine Bewertungen vor" in review_text:
                return None
            return float(soup.find('div', class_='mr-4').text)
        except Exception as e:
            print(f"Error extracting rating: {e}")
            return None

    # Private method to extract product links from a category page
    def _extract_all_product_links_in_category(self, category, soup, brands):
        has_next_page = soup.find(lambda tag: tag.name == 'span' and tag.get_text() == 'Weiter')
        index = 0
        brands_url = ""
        if brands:
            brands_url = "&brand=" + "+".join([re.sub(r"[' ]", "%20", brand.name) for brand in brands])

        while has_next_page and index < self._max_pages_to_scrape and not self._processed_last_page(index, soup):
            index += 1
            url = self._base_url + category.url + f'?page={index}{brands_url}'
            self._driver.get(url)
            soup = BeautifulSoup(self._driver.page_source, 'html.parser')

            for a in soup.find_all('a',class_='Q_opE0', href=True): yield a.get('href')
            has_next_page = soup.find(lambda tag: tag.name == 'span' and tag.get_text() == 'Weiter')

    # Private method to check if last page is processed
    def _processed_last_page(self, index, soup):
        weiter_button = soup.find('li', class_='l-Be8I')
        parent = weiter_button.parent
        return index - 1 == int(parent.contents[len(parent) - 2].text)

    # Private method to write the CSV header
    def _write_csv_header(self, file):
        writer = csv.writer(file, delimiter='|')
        writer.writerow(["Name", "Price", "Description", "Category", "Rating", "Source"])
        return writer

    # Private method to handle element location and action execution
    def _wait_until_element_located(self, by, value, action=None):
        try:
            wait = WebDriverWait(self._driver, 3)
            element = wait.until(EC.presence_of_element_located((by, value)))

            # Scroll the element into view and adjust for fixed header
            self._driver.execute_script("arguments[0].scrollIntoView();", element)
            self._driver.execute_script("window.scrollBy(0, -150);")  # Adjust for header height

            if action == 'click':
                element.click()
            elif action == 'text':
                return element.text
            elif action == 'get':
                return element
            return element
        except Exception as e:
            print(f"Element {value} not found: {e}")
            return None

    # Private method to create a data directory and prepare the CSV file path
    def _create_data_directory_and_csv(self):
        data_dir = os.path.join(os.getcwd(), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return os.path.join(data_dir, 'results.csv')
