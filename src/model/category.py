class Category:
    def __init__(self, name, url):
        self.name = name
        self.url = url
        # too complex for simple use-case
        # self.subcategories = []

    # will not be used due to performance issues
   # def add_subcategory(self, subcategory):
    #    self.subcategories.append(subcategory)
