import os

from flask import Flask
from flask_wtf.csrf import CSRFProtect
from config import Config
import coc
import asyncio
from dotenv import load_dotenv
load_dotenv()

csrf = CSRFProtect()
app = Flask(__name__)
def create_app():

    app.config.from_object(Config)

    csrf.init_app(app)


    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return  app