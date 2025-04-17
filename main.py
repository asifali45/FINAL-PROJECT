from app import app

# Import routes to register them
from routes import *

# Critical configuration: ensure secret key is set
app.secret_key = "form_digitizer_secure_secret_key_for_production"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
