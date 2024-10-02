import datetime

import pandas as pd
import re
import spacy
from deep_translator import GoogleTranslator
class PreProcessor:
    def __init__(self, file_path):
        # Load the dataset from the given file path (assuming it's a CSV)
        self.df = pd.read_csv(file_path, delimiter='|')
        # Initialize the translator
        self._translator = GoogleTranslator(source='de', target='en')
        # Load the spaCy NLP model for NER (Named Entity Recognition)
        self._nlp = spacy.load("en_core_web_sm")

    # Private function to extract the brand
    def _extract_brand(self, name):
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

    # Private function to translate text from German to English
    def _translate_text(self, text):
        # Define the character limit
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

        # Extract the brand
        brand, name = self._extract_brand(cleaned_name)


        # Translate name and description
        translated_name = self._translate_text(name)
        translated_description = self._translate_text(description)

        # Return processed data
        return pd.Series({
            'brand': brand,
            'name': translated_name,
            'description': translated_description
        })

    # Public method to process the entire dataset
    def process(self):
        now = datetime.datetime.now()
        # Apply the processing to each row of the DataFrame
        self.df[['brand', 'name', 'description']] = self.df.apply(self._process_row, axis=1)
        self.df.to_csv("/data/preprocessed.csv", index=False, sep='|')
        after = datetime.datetime.now()
        print(str(now) + str(after) + "     " + str(after-now))

# Usage example:
# processor = PreProcessor("myfile.csv")
# processed_df = processor.process()
# processed_df.to_csv("processed_file.csv", index=False)  # Save the processed file if needed
