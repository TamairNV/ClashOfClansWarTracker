from flask import Flask
from flask_wtf.csrf import CSRFProtect
from config import Config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

csrf = CSRFProtect()


def create_app():
    # 1. Create Flask Instance
    app = Flask(__name__)

    # 2. Load Config
    app.config.from_object(Config)

    # 3. Init Extensions
    csrf.init_app(app)

    # 4. Register Blueprints
    # We import here to avoid circular import issues
    from app.routes import main
    app.register_blueprint(main)

    return app


# This is the variable run_production.py looks for!
app = create_app()