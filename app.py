import os
import logging
from flask_migrate import Migrate
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from dotenv import load_dotenv
load_dotenv()


# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create the app
app = Flask(__name__)
# Set secret key - using a fixed key for now since SESSION_SECRET isn't available
app.secret_key = "dev_secure_secret_key_for_form_digitizer_application"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:12345678@localhost:5432/formdigitizer"

migrate = Migrate(app, db)
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Google Gemini API configuration
app.config["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_API_KEY", "")

# Log Google API configuration for debugging
google_api_key = os.environ.get("GOOGLE_API_KEY", "")
logging.debug(f"Google API key length: {len(google_api_key) if google_api_key else 0}")

# Configure CSRF protection
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = app.secret_key

# Initialize the extensions with the app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    # Import models
    from models import User, ExtractedForm  # noqa: F401
    
    # Create database tables
    db.create_all()
