
import os
from dotenv import load_dotenv
load_dotenv()

class Config:

    SECRET_KEY = 'devkey123'  # Replace with environment variable in production
    DEBUG = True
    TESTING = True
    # Clash of Clans API Credentials
    # You can use email/password for auto-key generation, or a static token
    COC_EMAIL = os.environ.get('COC_EMAIL')
    COC_PASSWORD = os.environ.get('COC_PASSWORD')


    # Clan Settings
    CLAN_TAG = "#8GGPQLPU"  # Replace with your real clan tag

    # Database Credentials
    DB_HOST = "192.168.1.60"
    DB_USER = "Home_User"
    DB_PASSWORD = "Tamer@2006"
    DB_NAME = "clash_manager"