from src.interdiscount.preprocessor import PreProcessor
from src.interdiscount.scraper import Scraper

def main():
    scraper = Scraper("http://www.interdiscount.ch")
    scraper.scrape()
    # preprocessor = PreProcessor("C:\\Users\\lucar\\switchdrive\\SyncVM\\Sem 2\\CIP\\project\\cip\\src\\interdiscount\\data\\raw-test.csv")
    # preprocessor.process()

   

if __name__ == "__main__":
    main()