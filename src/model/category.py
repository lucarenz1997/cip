class Category:
    def __init__(self, name, url, subcategories=None):
        self.name = name
        self.url = url
        self.subcategory = subcategories

    def __repr__(self):
        return f"Category(name={self.name}, url={self.url})"
