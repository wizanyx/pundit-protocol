import os
from tavily import TavilyClient
from openai import OpenAI
from dotenv import load_dotenv

# Load the keys from the hidden .env file
load_dotenv()

class NewsFetcher:
    def __init__(self):
        # Use os.getenv to pull the keys safely
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        # Initialize clients
        self.tavily = TavilyClient(api_key=self.tavily_key)
        self.client = OpenAI(api_key=self.openai_key)
