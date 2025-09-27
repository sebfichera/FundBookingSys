import os
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hash_pw, password):
    return check_password_hash(hash_pw, password)

def send_email(to_email, subject, body):
    mail_user = os.environ.get("MAIL_USERNAME")
    mail_pass = os.environ.get("MAIL_PASSWORD")
    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = int(os.environ.get("MAIL_PORT"))

    if not all([mail_user, mail_pass, mail_server, mail_port]):
        print("⚠️ Config mail non completa")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = mail_user
    msg['To'] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.starttls()
            server.login(mail_user, mail_pass)
            server.send_message(msg)
    except Exception as e:
        print(f"Errore invio mail: {e}")
