from flask import Flask
from routes import main

app = Flask(__name__)

# --- CRITICAL FIX: Register OUTSIDE the main block ---
# This ensures Waitress sees the routes when it imports 'app'
app.register_blueprint(main)

if __name__ == '__main__':
    app.run(debug=True, port=5001)