from src.interdiscount.scraper import Scraper

def main():

    # Instantiate the Scraper class
    scraper = Scraper("http://www.interdiscount.ch")
    scraper.scrape()

if __name__ == "__main__":
    main()