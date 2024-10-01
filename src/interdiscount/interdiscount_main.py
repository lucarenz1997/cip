from src.interdiscount.scraper import Scraper

def main():
    scraper = Scraper("http://www.interdiscount.ch")
    scraper.scrape()

if __name__ == "__main__":
    main()