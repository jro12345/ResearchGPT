"""Configuration file for ResearchGPT Assistant"""

import os
from dotenv import load_dotenv

class Config:
    def __init__(self):

        load_dotenv()
        
        self.MISTRAL_API_KEY = "7HKjZCOl049KPYbABsFwO4Yhg03kIUAx"
        self.validate_api_key()
        self.MODEL_NAME = "mistral-medium"  # Choose appropriate Mistral model
        self.TEMPERATURE = 0.1  # Set temperature for consistent responses
        self.MAX_TOKENS = 1000  # Set maximum response length
        
        self.DATA_DIR = "data/"
        self.SAMPLE_PAPERS_DIR = "data/sample_papers/"
        self.PROCESSED_DIR = "data/processed/"
        self.RESULTS_DIR = "results/"
        self.RESULTS_SUMMARIES_DIR = "results/summaries/"
        self.DOC_STATS_DIR = "results/doc_stats/"
        self.ANALYSES_DIR = "results/analyses/"
        
        self.CHUNK_SIZE = 1000  # Set text chunk size for processing
        self.OVERLAP = 100      # Set overlap between chunks

    def validate_api_key(self):
        """Validate the MISTRAL_API_KEY."""
        if not self.MISTRAL_API_KEY or self.MISTRAL_API_KEY.strip() == "":
            raise ValueError("MISTRAL_API_KEY is missing or invalid. Please replace the placeholder with a valid API key.")