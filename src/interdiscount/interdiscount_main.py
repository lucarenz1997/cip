from src.interdiscount.scraper import Scraper

def main():
    # Instantiate the Scraper class
    scraper = Scraper("http://www.amazon.de")

    all_categories = scraper.get_categories()
    desired_categories = ['Electronics & Photo', 'Computers']
    filtered_categories = list(filter(lambda category: category.name in desired_categories, all_categories))


    print(scraper.base_url)


if __name__ == "__main__":
    main()