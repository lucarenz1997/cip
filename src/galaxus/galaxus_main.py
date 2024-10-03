from src.galaxus.preprocessor import PreProcessor
from src.galaxus.scraper import Scraper

def main():
    scraper = Scraper("http://www.galaxus.ch")
    scraper.scrape()
    preprocessor = PreProcessor("data\\raw.csv")
    preprocessor.process()

   

if __name__ == "__main__":
    main()


