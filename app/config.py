import datetime
import os


class Config(object):
    """Parent configuration class."""
    DEBUG = False
    CSRF_ENABLED = True
    # gets variables from environment
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=30)
    DATABASE_URI = os.getenv("DATABASE_URI")
    if DATABASE_URI == None:
        DATABASE_URI = os.getenv("LOCAL_DATABASE_URI", "Not found")

    EMAIL_SECURITY_PASSWORD_SALT = os.getenv('EMAIL_SECURITY_PASSWORD_SALT')
    # Mail Settings
    MAIL_DEFAULT_SENDER = "noreply@kalakriti.com"
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_DEBUG = False
    MAIL_USERNAME = os.getenv("EMAIL_USER")
    MAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    S3_ENDPOINT = os.getenv("S3_ENDPOINT")
    S3_BUCKET = os.getenv("S3_BUCKET")
    S3_VIDEO_BUCKET = os.getenv("S3_VIDEO_BUCKET")
    S3_KEY = os.getenv("S3_KEY")
    S3_SECRET = os.getenv("S3_SECRET")
    S3_LOCATION = os.getenv("S3_LOCATION")


class DevelopmentConfig(Config):
    """Configurations for Development."""
    DEBUG = True


class TestingConfig(Config):
    """Configurations for Testing, with a separate test database."""
    TESTING = True
    DEBUG = True


class StagingConfig(Config):
    """Configurations for Staging."""
    DEBUG = True


class ProductionConfig(Config):
    """Configurations for Production."""
    DEBUG = False
    TESTING = False


app_config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
}
