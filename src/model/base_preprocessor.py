from abc import ABC, abstractmethod

import pandas as pd


class BasePreProcessor(ABC):

    def __init__(self, file_path, delim='|'):
        # Load the dataset from the given file path
        self.df = pd.read_csv(file_path, delimiter=delim)

    @abstractmethod
    def process(self):
        """
        EACH PREPROCESSOR MUST IMPLEMENT THE METHOD
        """
        pass
