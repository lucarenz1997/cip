import datetime

import pandas as pd
import re
import spacy
from deep_translator import GoogleTranslator

from src.model.base_preprocessor import BasePreProcessor
from src.utils.log_executor_decorator import log_execution


class PreProcessor(BasePreProcessor):
    def __init__(self, file_path):
        super().__init__(file_path)
        # Initialize the translator
        self._translator = GoogleTranslator(source='de', target='en')
        # Load the spaCy NLP model for NER (Named Entity Recognition)
        self._nlp = spacy.load("en_core_web_sm")

    # Private function to extract the brand. For most cases, brands were somewhat easily extracted.
    # For the other cases, NLP is used to extract the brand
    def _extract_brand(self, name, brand):
        if brand == '':

            possible_brand = self._extract_uppercase_words(name)
            doc = self._nlp(possible_brand)
            brand = None

            # Loop through entities identified by NER
            for ent in doc.ents:
                if ent.label_ == "ORG":  # 'ORG' label typically refers to organizations/brands
                    brand = ent.text
                    break

            # If no brand is detected, fall back to a simple heuristic
            if not brand:
                brand = possible_brand

        return brand, name[len(brand):].strip()


    def _extract_uppercase_words(self, name):
        # Match all uppercase words until the first lowercase or mixed-case word is found
        match = re.match(r'^([A-Z\s\W]+)(?=\b[a-zA-Z])', name)

        # If a match is found, return it, otherwise return an empty string
        return match.group(0).strip() if match else ''

    # Private function to clean leading non-alphanumeric characters
    def _clean_text(self, text):
        # If the text is not a string, return an empty string
        if not isinstance(text, str):
            return ''
        return re.sub(r'^[^a-zA-Z0-9]+', '', text)

    # Private function to translate text from German to English (very time-consuming!)
    def _translate_text(self, text):
        # Define the character limit as we cannot translate more than 5k chars at once
        max_chars = 5000

        # Convert the text to a string if it isn't one already
        if not isinstance(text, str):
            return ''

        # If the text is within the character limit, translate directly
        if len(text) <= max_chars:
            return self._translator.translate(text)

        # Otherwise, split the text into chunks and translate each chunk
        translated_text = ""
        for i in range(0, len(text), max_chars):
            chunk = text[i:i + max_chars]
            translated_text += self._translator.translate(chunk) + " "

        return translated_text.strip()

    # Private function to process each row
    def _process_row(self, row):
        # Clean the name and description
        cleaned_name = self._clean_text(row['name'])
        description = self._clean_text(row['description'])

        brand = self._clean_text(row['brand'])
        category = row['category']
        sub_category = row['sub_category']

        # Extract the brand and update the name accordingly
        brand, name = self._extract_brand(cleaned_name, brand)


        # Translate name, description and category (again: time-consuming)
        translated_name = self._translate_text(name)
        translated_description = self._translate_text(description)
        tranlsated_category = self._translate_text(category)
        tranlsated_sub_category = self._translate_text(category)

        # Return processed data
        return pd.Series({
            'brand': brand,
            'name': translated_name,
            'description': translated_description,
            'category': tranlsated_category,
            'sub_category': tranlsated_sub_category,
            'source': "interdiscount"
        })

    # Public method to process the entire dataset
    @log_execution
    def process(self):
        start = datetime.datetime.now()
        total_rows = len(self.df)
        progress_interval = total_rows // 100 if total_rows >= 100 else 1  # Determine when to update the progress

        # Apply the processing to each row of the DataFrame
        for idx, row in self.df.iterrows():
            self.df.loc[idx, ['brand', 'name', 'description', 'category', 'sub_category', 'source']] = self._process_row(row)

            # Show progress for every 1% of the total rows
            if idx % progress_interval == 0:
                percentage = (idx / total_rows) * 100
                print(f"Progress: {percentage:.2f}%")

        # Save the processed file
        self.df.to_csv("data/preprocessed.csv", index=False, sep='|')

        # Time tracking
        after = datetime.datetime.now()
        print(f"Started: {start}, Ended: {after}, Duration: {after - start}")
