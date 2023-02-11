from flask_mail import Message

# from app import app, mail
from flask import current_app as app
import app.main as main


def send_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=app.config["MAIL_DEFAULT_SENDER"],
    )
    main.mail.send(msg)
