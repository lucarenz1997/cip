from src.interdiscount.scraper import Scraper

def main():
    # Instantiate the Scraper class
    scraper = Scraper("http://www.interdiscount.ch")
    result = scraper.scrape()
    scraper.quit_driver()



if __name__ == "__main__":
    main()