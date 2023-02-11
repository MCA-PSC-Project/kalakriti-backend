import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env file into environment

from app.app import create_app

config_name = os.getenv('APP_CONFIG') # app_config = "development"
app = create_app(config_name)

if __name__ == '__main__':
    app.run()
