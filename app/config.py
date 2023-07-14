import datetime
import os


class Config(object):
    """Parent configuration class."""

    DEBUG = False
    CSRF_ENABLED = True
    # gets variables from environment
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=10)
    JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=30)
    DATABASE_URI = os.getenv("DATABASE_URI")
    if DATABASE_URI == None:
        DATABASE_URI = os.getenv("LOCAL_DATABASE_URI", None)

    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL == None:
        REDIS_URL = os.getenv("LOCAL_REDIS_URL", None)

    EMAIL_SECURITY_PASSWORD_SALT = os.getenv("EMAIL_SECURITY_PASSWORD_SALT")
    # Mail Settings
    MAIL_DEFAULT_SENDER = "kalakriti.email@gmail.com"
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

    SEND_EMAIL = False
    SEND_MOTP = False

    APP_NAME = os.getenv("APP_NAME")


class DevelopmentConfig(Config):
    """Configurations for Development."""

    DEBUG = True


class TestingConfig(Config):
    """Configurations for Testing, with a separate test database."""

    # sending mail won't work when testing is true
    TESTING = True
    DEBUG = True
    SEND_EMAIL = True
    SEND_MOTP = True


class StagingConfig(Config):
    """Configurations for Staging."""

    DEBUG = True
    SEND_EMAIL = True
    SEND_MOTP = True
    # MAIL_DEBUG = True


class ProductionConfig(Config):
    """Configurations for Production."""

    DEBUG = False
    TESTING = False
    SEND_EMAIL = True
    SEND_MOTP = True
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=30)


app_config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
}
