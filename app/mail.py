from flask_mail import Message

# from app import app, mail
from flask import current_app as app
import app.app_globals as app_globals


def send_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=app.config["MAIL_DEFAULT_SENDER"],
    )
    app_globals.mail.send(msg)
