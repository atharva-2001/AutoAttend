"""Loads environment variables from .env file."""
import os
import pathlib
import yaml
from dotenv import load_dotenv
import secrets

load_dotenv('../.env')

class Config:
    """Configuration class for the application."""
    API_URL = os.getenv('API_URL')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')
    API_PREFIX = os.getenv('API_PREFIX')
