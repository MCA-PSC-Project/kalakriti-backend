from itsdangerous import URLSafeTimedSerializer
from flask import current_app as app


def generate_email_token(email):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return serializer.dumps(email, salt=app.config["EMAIL_SECURITY_PASSWORD_SALT"])


def verify_email_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        email = serializer.loads(
            token, salt=app.config["EMAIL_SECURITY_PASSWORD_SALT"], max_age=expiration
        )
        return email
    except Exception:
        return False
