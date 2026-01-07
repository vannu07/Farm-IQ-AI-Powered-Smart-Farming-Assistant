"""Configuration module for Farm-IQ application."""
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Weather API Key - try to get from environment variable first, then fall back to default
weather_api_key = os.getenv("WEATHER_API_KEY", "0e6937bbe4074774987cbe2e17df6ed6")
