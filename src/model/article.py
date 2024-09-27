##
##  Most general model that will be used for each individual type of article
##
class Article:
    def __init__(self, name, price, description):
        self.name = name
        self.price = price
        self.description = description
