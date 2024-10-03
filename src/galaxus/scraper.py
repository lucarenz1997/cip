from src.model.base_scraper import BaseScraper
from src.utils.log_executor_decorator import log_execution


# Scraper class for scraping articles from Galaxus website.
class Scraper(BaseScraper):
    _max_pages_to_scrape = 40  # each page has 24 articles
    _save_interval = 200  # Accumulate data into the dataframe every 100 articles

    def __init__(self, base_url):
        super().__init__(base_url)
        self._article_data = []  # Temporary list to store article data

    @log_execution
    def scrape(self):
        categories = self._get_categories()

    def _get_categories(self):
        print(f"Fetching categories from {self._base_url}")
        soup = self._get_dynamic_soup(self._base_url)

        # Debugging: Print the HTML to check if the page was fetched correctly
        print(soup.prettify())

        navigation_bar = soup.findAll('li', class_='sc-ba0f659-0')  # Adjust class based on actual HTML
        print(f"Found {len(navigation_bar)} navigation items.")

        categories = []
        for li in navigation_bar:
            a_tag = li.find('a')  # Find the 'a' tag inside the 'li' tag
            if a_tag:
                text = a_tag.text.strip()  # Get the text of the 'a' tag, removing extra whitespace
                href = a_tag.get('href')  # Get the 'href' attribute of the 'a' tag
                print(f"Category found: {text}, URL: {href}")
                if text and href:
                    categories.append((text, href))
        return categories
