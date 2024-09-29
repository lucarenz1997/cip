##
##  Most general model that will be used for each individual type of article
##
class Article:
    def __init__(self, name, price, description, category, rating):
        self.name = name
        self.price = price
        self.description = description
        self.category = category
        self.rating = rating
