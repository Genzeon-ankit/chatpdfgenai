from flask import Flask
import os
from flask_cors import CORS
from routes import routes_blueprint
import config

# Initialize Flask app
app = Flask(__name__)

# Register the routes blueprint
app.register_blueprint(routes_blueprint)

# Set up CORS
CORS(app, origins="*")

# Bind the cache to the app
config.cache.init_app(app)

app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
if not os.path.exists(config.UPLOAD_FOLDER):
    os.makedirs(config.UPLOAD_FOLDER)

if __name__ == '__main__':
    app.run(port=5000)
