import os
from dotenv import load_dotenv
load_dotenv()

class Config:

    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    TESTING = False
    # Clash of Clans API Credentials
    COC_EMAIL = os.environ.get('COC_EMAIL')
    COC_PASSWORD = os.environ.get('COC_PASSWORD')


    # Clan Settings
    CLAN_TAG = os.environ.get('CLAN_TAG', '#8GGPQLPU')

    # Database Credentials (set in .env)
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_NAME = os.environ.get('DB_NAME', 'clash_manager')
