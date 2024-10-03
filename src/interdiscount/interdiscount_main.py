from src.interdiscount.preprocessor import PreProcessor
from src.interdiscount.scraper import Scraper

def main():
    scraper = Scraper("http://www.interdiscount.ch")
    scraper.scrape()
    preprocessor = PreProcessor("data\\raw.csv")
    preprocessor.process()

   

if __name__ == "__main__":
    main()