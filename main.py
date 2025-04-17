import os
import logging
from app import app

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import routes to register them
from routes import *

# The secret key is already configured in app.py, no need to set it again here
# which could potentially overwrite the working configuration

# Google API key is also already configured in app.py

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
