from src.model.article import Article

class Book(Article):
    def __init__(self, name, price, description, author, publisher, publication_date, isbn):
        super().__init__(name, price, description)
        self.author = author
        self.publisher = publisher
        self.publication_date = publication_date
        self.isbn = isbn