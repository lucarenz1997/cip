from src.model.article import Article

class InterdiscountArticle(Article):
    def __init__(self, name, price, description, category, rating, brand, source, sub_category):
        super().__init__(name, price, description, category, rating, brand, source)
        self.sub_category = sub_category