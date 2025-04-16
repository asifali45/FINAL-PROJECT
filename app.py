import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///formdigitizer.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Azure Form Recognizer configuration
app.config["AZURE_ENDPOINT"] = "https://asifali.cognitiveservices.azure.com/"
app.config["AZURE_KEY"] = "EOE9RXRJ4kGTaKDMpkijz3eru1bSarEcRShgxcYEbl9qmpzekr7FJQQJ99BCACGhslBXJ3w3AAAFACOG9wU8"

# Log Azure configuration for debugging
logging.debug(f"Azure endpoint: {app.config['AZURE_ENDPOINT']}")
logging.debug(f"Azure key length: {len(app.config['AZURE_KEY']) if app.config['AZURE_KEY'] else 0}")

# Initialize the extensions with the app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    # Import models
    from models import User, ExtractedForm  # noqa: F401
    
    # Create database tables
    db.create_all()
