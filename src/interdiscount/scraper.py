from bs4 import BeautifulSoup

from src.model.category import Category
from src.utils.requester_util import createRequest

class Scraper:
    def __init__(self, base_url):
        self._base_url = base_url

    def get_soup(self):
        return BeautifulSoup(createRequest(self.base_url), 'html.parser')

    @property
    def base_url(self):
        return self._base_url

    # GET ALL CATEGORIES AND ITS CORRESPONDING URLS
    def get_categories(self):
        soup = self.get_soup()
        navigation_bar = soup.find('header').find('div', id='nav-main').find('div', class_='nav-fill').find('div', class_='nav-progressive-content').findAll('a', href=True, class_='nav-a')
        categories = []
        for category in navigation_bar:
            category_name = category.get_text(strip=True)
            category_url = category.get('href')
            print("Getting info for category: ", category_name)
            category_instance = Category(category_name, category_url)
            categories.append(category_instance)
            # COMMENTED OUT DUE TO PERFORMANCE ISSUES (<30 minutes to scrape all its subcategories)
            # If this category has subcategories, add them to the category_instance.
            # subcategories = self.get_subcategories(category_url)
            # for subcategory in subcategories:
            #     category_instance.add_subcategory(subcategory)
        return categories

    def get_subcategories(self, category_url):
        print("Getting next subcategory")
        # Get the HTML content of the category page
        content = createRequest(self.base_url + category_url)
        # Parse the HTML content
        soup = BeautifulSoup(content, 'html.parser')

        categories_list = soup.find_all('a', class_='octopus-pc-category-card-v2-category-link')
        subcategories = []
        for element in categories_list:
            # Extract the name and URL of the subcategory
            subcategory_name = element.get_text(strip=True)
            subcategory_url = element.get('href')
            # Create a Category instance for the subcategory
            subcategory = Category(subcategory_name, subcategory_url)
            subcategories.append(subcategory)
            sub_subcategories = self.get_subcategories(subcategory_url)
            for sub_subcategory in sub_subcategories:
                subcategory.add_subcategory(sub_subcategory)

        return subcategories

