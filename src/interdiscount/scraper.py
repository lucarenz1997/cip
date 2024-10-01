import csv
import os
import gc
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.interdiscount.Brand import Brand
from src.model.article import Article
from src.model.category import Category
from src.utils.log_executor_decorator import log_execution
import tkinter as tk
from tkinter import messagebox
import re


class Scraper:
    batch_size = 100  # Add a batch size to control memory usage
    max_pages_to_scrape = 25

    def _get_all_brands(self):
        self.wait_until_element_located(By.CLASS_NAME, '_2HIFC0', 'click')  # open brands
        # firstBrand = self.wait_until_element_located(By.CLASS_NAME, '_2hoAcL','get').text
        div_with_all_brands = self.wait_until_element_located(By.CLASS_NAME, '_1o-3dE',
                                                              'get')  # div containing all brands
        all_labels = div_with_all_brands.find_elements(By.TAG_NAME, value='label')
        brands = []
        for label in all_labels:  # label.text = 'Brand (123)'
            match = re.match(r'(.*?)\s*\((\d+)\)', label.text)
            if match:
                brand_name = match.group(1).strip()
                article_count = int(match.group(2))
                brand = Brand(brand_name, article_count)
                brands.append(brand)
        # self.wait_until_element_located(By.CLASS_NAME, '_2HIFC0', 'click') # close brands dropdown
        return brands

    def select_brands(self, brands):
        selected_objects = []  # Declare this in the outer scope

        def on_ok():
            nonlocal selected_objects  # Reference the outer scope
            selected_indices = listbox.curselection()
            selected_objects = [brands[i] for i in selected_indices]
            root.destroy()  # Close the popup window

        root = tk.Tk()
        root.title("Select the brands that you want to scrape")

        screen_height = root.winfo_screenheight()
        window_height = int(screen_height * 0.4)  # Set the window height to 40% of the screen height
        root.geometry(f"400x{window_height}")  # Set window size, width is fixed at 400

        # Create a frame for the Listbox and Scrollbar
        frame = tk.Frame(root)
        frame.pack(fill=tk.BOTH, expand=True)

        # Create a Scrollbar and associate it with the Listbox
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create a Listbox with multiple selection mode
        listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=window_height // 20,  # Calculate appropriate height
                             yscrollcommand=scrollbar.set)

        for brand in brands:
            listbox.insert(tk.END, f"{brand.name} ({brand.article_count} articles)")
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=listbox.yview)

        # Create an OK button and pack it below the list
        ok_button = tk.Button(root, text="OK", command=on_ok)
        ok_button.pack(pady=10)  # Add padding to ensure visibility

        root.mainloop()
        return selected_objects  # Return the selected objects

    def select_categories(self, objects):
        selected_objects = []  # Declare this in the outer scope

        def on_ok():
            nonlocal selected_objects  # Reference the outer scope
            selected_indices = listbox.curselection()
            selected_objects = [objects[i] for i in selected_indices]
            root.destroy()  # Close the popup window

        root = tk.Tk()
        root.title("Select the categories that you want to scrape")

        screen_height = root.winfo_screenheight()
        window_height = int(screen_height * 0.4)  # Set the window height to 40% of the screen height
        root.geometry(f"400x{window_height}")  # Set window size, width is fixed at 400

        # Create a frame for the Listbox and Scrollbar
        frame = tk.Frame(root)
        frame.pack(fill=tk.BOTH, expand=True)

        # Create a Scrollbar and associate it with the Listbox
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create a Listbox with multiple selection mode
        listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=window_height // 20,  # Calculate appropriate height
                             yscrollcommand=scrollbar.set)

        for obj in objects:
            listbox.insert(tk.END, obj.name)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=listbox.yview)

        # Create an OK button and pack it below the list
        ok_button = tk.Button(root, text="OK", command=on_ok)
        ok_button.pack(pady=10)  # Add padding to ensure visibility

        root.mainloop()
        return selected_objects  # Return the selected objects

    def ask_interactive_mode(self):
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        result = messagebox.askquestion("Interactive Mode", "Do you want to scrape in interactive mode?",
                                        icon='warning')
        root.destroy()  # Destroy the main window
        return result

    def __init__(self, base_url):
        self._base_url = base_url
        self.driver = self.create_driver()
        self.interactive_mode = self.ask_interactive_mode() == 'yes'

    def create_driver(self):
        driver = webdriver.Firefox()
        return driver

    def get_dynamic_soup(self, url=None):
        if url:
            self.driver.get(url)
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    def quit_driver(self):
        self.driver.quit()
        print("driver quit")

    def processed_last_page(self, index, soup):
        weiter_button = soup.find('li', class_='l-Be8I')
        parent = weiter_button.parent
        return index - 1 == int(parent.contents[len(parent) - 2].text)

    @property
    def base_url(self):
        return self._base_url

    def scrape(self):
        categories = self._get_categories()

        if self.interactive_mode:
            categories = self.select_categories(categories)

        self._close_cookie_banner()
        data_dir = os.path.join(os.getcwd(), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        csv_file_path = os.path.join(data_dir, 'results.csv')
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = self._writeHeader(file)
            for category in categories:
                if category.url:
                    # get all urls for articles in category
                    for article in self._scrape_category(category):
                        writer.writerow([article.name, article.price, article.description, article.category.name,
                                         article.rating, article.source])
        self.quit_driver()

    def _writeHeader(self, file):
        writer = csv.writer(file, delimiter='|')
        writer.writerow(
            ["Name", "Price", "Description", "Category", "Rating", "Source"])  # Write the header
        return writer

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
    def _scrape_category(self, category):
        self.driver.get(self.base_url + category.url + '?page=1')
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        if self.interactive_mode:
            brands = self.select_brands(self._get_all_brands())
        else:
            brands = []

        article_count = 0
        for article_link in self._extract_all_product_links_in_category(category, soup, brands):
            yield self._extract_data(article_link, category)

            article_count += 1
            if article_count % self.batch_size == 0:
                self._release_memory()

    def _release_memory(self):
        # Close and reopen the browser to free memory
        self.quit_driver()
        self.driver = self.create_driver()
        self._close_cookie_banner()

        # Explicitly call garbage collector
        gc.collect()

    @log_execution
    def _extract_all_product_links_in_category(self, category, soup, brands):
        article_links = []
        has_next_page = soup.find(lambda tag: tag.name == 'span' and tag.get_text() == 'Weiter')
        index = 0
        brands_url = ""
        if len(brands) != 0:
            brands_url = "&brand=" + "+".join([str(brand.name)
                                              .replace(" ", "%20")
                                              .replace("'", "%27") for brand in brands])

        while has_next_page and index < self.max_pages_to_scrape and not self.processed_last_page(index, soup):
            index += 1
            url = self.base_url + category.url + '?page=' + str(index) + brands_url
            self.driver.get(url)  # '&sort=price-desc' not allowed according to robots.txt
            # Update the BeautifulSoup object
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Scrape the links from the page
            for a in soup.find_all('a', class_='Q_opE0', href=True):
                yield a.get('href')
            has_next_page = soup.find(lambda tag: tag.name == 'span' and tag.get_text() == 'Weiter')

    def _extract_data(self, article_link, category):
        soup = self._setup_soup(article_link)
        price = self._get_price(soup)
        name = soup.find('h1').contents[0].text
        description = self._get_description(soup)
        rating = self._get_rating(soup)
        article = Article(name, price, description, category, rating, "interdiscount")
        return article

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
            review_text = self.wait_until_element_located(By.XPATH, f"//*[@id='collapsible-reviews-controls']", 'text')
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
        description = soup.find('div', attrs={'data-testid': 'text-clamp'}).contents[0].text.replace("\n", " ")
        return description if description and description.strip() else None

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
            elif action == 'get':
                return element
            return element
        except Exception as e:
            print("Element does not exist", e)
