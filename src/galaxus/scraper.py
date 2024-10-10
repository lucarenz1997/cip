import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from src.model.article import Article
from src.model.base_scraper import BaseScraper
from src.model.brand import Brand
from src.model.category import Category
from src.utils.log_executor_decorator import log_execution
from src.utils.ui_utils import UIUtils
from selenium.webdriver.support import expected_conditions as EC


# Scraper class for scraping articles from Galaxus website.
class Scraper(BaseScraper):
    _ignored_categories = ['Sale', 'Used']
    _max_pages_to_scrape = 40  # each page has 24 articles
    _save_interval = 200  # Accumulate data into the dataframe every 100 articles

    def __init__(self, base_url):
        super().__init__(base_url)
        self._article_data = []  # Temporary list to store article data
        self._df = pd.DataFrame(
            columns=["name", "price", "description", "category", "rating", "brand",
                     "source"])

    @log_execution
    def scrape(self):
        categories = self._get_categories()
        selected_categories = UIUtils.show_selection_window_dropdown(categories,
                                                                     "Select the categories that you want to scrape")

        for category in selected_categories:
            for article in self._scrape_category(category):
                # Add each article to the temporary list
                self._article_data.append({
                    "name": article.name,
                    "price": article.price,
                    "description": article.description,
                    "category": article.category.name,
                    "rating": article.rating,
                    "brand": article.brand
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


    def _get_categories(self):
        print(f"Fetching categories from {self._base_url}")
        soup = self._update_soup(self._base_url, sleep_timer=0.3)

        navigation_bar = soup.findAll('li', class_='sc-ba0f659-0')
        print(f"Found {len(navigation_bar)} navigation items.")

        categories = []
        for li in navigation_bar:
            a_tag = li.find('a')  # Find the 'a' tag inside the 'li' tag
            if a_tag:
                text = a_tag.text.strip()  # Get the text of the 'a' tag, removing extra whitespace
                href = a_tag.get('href')  # Get the 'href' attribute of the 'a' tag
                print(f"Category found: {text}, URL: {href}")
                if text and href and (text not in self._ignored_categories):
                    categories.append(Category(text, href, self._get_subcategories(href)))
        return categories

    def _get_subcategories(self, link):
        soup = self._update_soup(self._base_url + link)
        list_items = soup.find('ul', class_="sc-1656bbdd-0 gQqszz").contents
        sub_categories = []
        for subcat in list_items:
            a_subcat = subcat.find('a')
            sub_categories.append(Category(a_subcat.text, a_subcat.get('href'), None))
        return sub_categories

    def _get_all_brands(self, category):
        print(f'Getting all brands in category {category.name}')
        # self._update_soup(self._base_url + category.url, sleep_timer=0.3)
        self._wait_until_element_located(By.XPATH, "//*[@aria-label='Brand']", 'click', sleep_time=2)
        time.sleep(1)
        soup = BeautifulSoup(self._driver.page_source, 'html.parser')
        brands = []
        for brand_area in soup.find('ul', class_='sc-b9093e7f-7 iiBANC').findAll('li'):
            brand_name = brand_area.find('span', class_='sc-2b1c90df-1 kvYprx').text
            article_count = int(brand_area.find('span', class_='sc-2b1c90df-2 dfAmFV').text)
            if article_count != 0:
                brands.append(Brand(brand_name, article_count))
        return brands

    def _scrape_category(self, category):
        print(f'Scraping category {category.name}')
        sub_categories = self._get_all_sub_categories(category)
        selected_sub_categories = UIUtils.show_selection_window(sub_categories,
                                                                "Select the subcategories that you want to scrape")
        self._click_on_selected_sub_categories(selected_sub_categories)

        brands = self._get_all_brands(category)
        selected_brands = UIUtils.show_selection_window(brands, "Select the brands that you want to scrape")
        self._click_on_selected_brands(selected_brands)

        # get the p with class = 'sc-e1fe84e1-2 hZKDCk' and get the "of X" number
        soup = BeautifulSoup(self._driver.page_source, 'html.parser')
        try:
            product_count = soup.find('p', class_='sc-e1fe84e1-2 hZKDCk').text.split(" of ")[1].split()[0]  # Get the first number after 'of'
            take_amount = 24
            while take_amount < int(
                    product_count):  # the page loads 24 max at first. and then increments always 60 articles
                take_amount += 60
            soup = self._update_soup(self._driver.current_url + f'&take={str(take_amount)}', sleep_timer=3)
        except:
            # less than 24 articles are on the page
            pass

        article_list = []
        print(f'Getting all articles')
        for article in self._driver.find_elements(By.CSS_SELECTOR, "article.sc-328a7c4f-1.dBtYoI"):
            self._driver.execute_script("arguments[0].scrollIntoView();", article)
            time.sleep(0.4)
            ref = article.find_element(By.TAG_NAME, 'a').get_property('href')
            article_list.append(ref)

        article_count = 0
        for link in article_list:
            yield self._extract_article_data(link, category)
            article_count +=1
            if article_count % 300 == 0:
                self._release_memory()

    # todo can be refactored
    def _get_all_sub_categories(self, category):
        print(f'Getting all sub categories from {category.name}')
        self._update_soup(self._base_url + category.url, sleep_timer=0.3)
        self._wait_until_element_located(By.XPATH, "//*[@aria-label='Category']", 'click', sleep_time=2)
        time.sleep(1)
        soup = BeautifulSoup(self._driver.page_source, 'html.parser')

        sub_categories = []
        for category_area in soup.find('ul', class_='sc-b9093e7f-7 iiBANC').findAll('li'):
            article_count = int(category_area.find('span', class_='sc-2b1c90df-2 dfAmFV').text)
            category_name = category_area.find('span', class_='sc-2b1c90df-1 kvYprx').text
            if article_count != 0:
                sub_categories.append(Category(category_name, article_count))
        return sub_categories

    def _click_on_selected_brands(self, brands):
        for brand in brands:
            # selects all brands by clicking on the "checkbox" (due to brand encoding for url)
            span_with_brand_name = WebDriverWait(self._driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, f"//div[@id='bra']//span[@class='sc-2b1c90df-1 kvYprx' and text()='{brand.name}']")))

            parent = span_with_brand_name.find_element(By.XPATH, "./..")
            checkbox_span = parent.find_element(By.XPATH, "./span[1]")
            self._driver.execute_script("arguments[0].scrollIntoView();", checkbox_span)
            time.sleep(0.1)
            self._driver.execute_script("window.scrollBy(0, -150);")
            checkbox_span.click()
            time.sleep(0.8)

        apply_brands_button = self._driver.find_element(By.CSS_SELECTOR,
                                                        "button.sc-162db2fb-0.myuCZ.sc-162db2fb-1.sc-7707229f-2.kRbzeV.eCnljM")
        apply_brands_button.click()

    def _click_on_selected_sub_categories(self, selected_sub_categories):
        for sub_category in selected_sub_categories:
            # selects all brands by clicking on the "checkbox" (due to sub_category encoding for url)
            span_with_brand_name = WebDriverWait(self._driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, f"//div[@id='pt']//span[@class='sc-2b1c90df-1 kvYprx' and text()='{sub_category.name}']")))

            parent = span_with_brand_name.find_element(By.XPATH, "./..")
            checkbox_span = parent.find_element(By.XPATH, "./span[1]")
            self._driver.execute_script("arguments[0].scrollIntoView();", checkbox_span)
            time.sleep(0.1)
            self._driver.execute_script("window.scrollBy(0, -150);")
            checkbox_span.click()
            time.sleep(0.1)

        apply_brands_button = self._driver.find_element(By.CSS_SELECTOR,
                                                        "button.sc-162db2fb-0.myuCZ.sc-162db2fb-1.sc-7707229f-2.kRbzeV.eCnljM")
        apply_brands_button.click()
        pass

    def _extract_article_data(self, link, category):
        soup = self._update_soup(link)

        try:
            self._driver.execute_script("arguments[0].scrollIntoView();",
                                        self._driver.find_element(By.ID, ':R5ct9e6d1tm:'))

        except Exception as e:
            print("not scrollable into",e)

        time.sleep(2)

        try:

            # specifications = self._driver.find_elements(By.ID, 'specifications')[0].click()

            show_more = self._driver.find_element(By.CSS_SELECTOR, "button[data-test='showMoreButton-specifications']")
            self._driver.execute_script("arguments[0].scrollIntoView();", show_more)

            time.sleep(0.4)
            self._driver.execute_script("window.scrollBy(0, -350);")
            time.sleep(0.5)
            show_more.click()
            # self._driver.execute_script("arguments[0].scrollIntoView();", specifications)
            # time.sleep(1)
            # self._driver.execute_script("window.scrollBy(0, 100);")
            # self._wait_until_element_located(By.CSS_SELECTOR, "button[data-test='showMoreButton-specifications']", 'click', sleep_time=1)
            soup = self._update_soup()
            time.sleep(0.2)
            specs = soup.findAll('a', class_='sc-972af934-0 hoQmUQ')
            if len(specs) > 0:
                brand = specs[0].text.replace("\n", " ").strip()  # Make sure to use strip to remove extra spaces
            else:
                brand = None

            if len(specs) > 1:
                found_category = specs[1].text.replace("\n", " ").strip()
            else:
                found_category = category  # Use the default category if not found
        except Exception as e:
            brand = None
            found_category = category


        article_name = soup.find('h1').text
        price = float(soup.find('button', class_='sc-d8df8e48-5 ccjwlK').text.replace(".–", '').replace("’", "").replace(
            'CHF', ''))

        try:
            self._wait_until_element_located(By.CSS_SELECTOR, "button[data-test='ShowMoreToggleButton-description']",'click')
        except Exception as e:
            # description is already complete
            pass

        soup = self._update_soup()
        description = soup.find('div', class_='sc-5a972e05-0 jzGCwC').text.replace("\n", " ")
        try:
             rating = float(soup.find('div', class_='sc-98a81fa6-0 UIRot').find('span', class_='sc-218358ee-2 sc-218358ee-3 jltNFx bFfwDd star_stars__LYfBH sc-d9dbbd3c-1 jsBVEW').get('aria-label').split(" out")[0])
        except Exception as e:
            rating = None
        return Article(article_name, price, description, Category(found_category, None, None), rating, brand)
