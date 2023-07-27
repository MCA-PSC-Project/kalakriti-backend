import os
from dotenv import load_dotenv
import logging
import sys

load_dotenv()  # loads variables from .env file into environment

from app.app import create_app

config_name = os.getenv("APP_CONFIG")  # app_config = "development"
app = create_app(config_name)

print(f"__name__ = {__name__}")

if "gunicorn" in sys.modules:
    # Flask application is being run through gunicorn
    app.logger.debug("Flask application is being run through gunicorn")
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
else:
    # Flask application is being run on localhost
    # app.logger.debug("Flask application is being run on localhost")
    app.logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    app.logger.addHandler(handler)

if __name__ == "__main__":
    # Flask application is being run directly
    app.run()
