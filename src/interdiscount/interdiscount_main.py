from src.interdiscount.scraper import Scraper

def main():
    # Instantiate the Scraper class
    Scraper("http://www.interdiscount.ch").scrape()

if __name__ == "__main__":
    main()