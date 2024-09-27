import requests
from bs4 import BeautifulSoup
from src.utils.requesterUtil import createRequest

BASE_URL = "http://www.amazon.de"

# Create a BeautifulSoup object and specify the parser
soup = BeautifulSoup(createRequest(BASE_URL), 'html.parser')


# Get the navigation bar and get all links to the categories
navigation_bar = soup.find('header').find('div', id='nav-main').find('div', class_='nav-fill').find('div', class_='nav-progressive-content').findAll('a', href=True, class_='nav-a')
cat_dict = {}
for category in navigation_bar:
    cat_dict[category.get_text(strip=True)] = category.get('href')

print(cat_dict)