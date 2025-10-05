import os
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
import threading

ASYNC_EMAIL = os.environ.get("ASYNC_EMAIL", "true").lower() == "true"

# -------------------
# Password utilities
# -------------------
def hash_password(password: str) -> str:
    """Hash di una password"""
    return generate_password_hash(password)

def verify_password(hash_pw: str, password: str) -> bool:
    """Verifica che la password corrisponda all'hash"""
    return check_password_hash(hash_pw, password)

# -------------------
# Email utilities
# -------------------
# ----------------- Password -----------------
def hash_password(password):
    return generate_password_hash(password)

def verify_password(hash_pw, password):
    return check_password_hash(hash_pw, password)

# ----------------- Invio email -----------------
def send_email(to_email, subject, body):
    """
    Funzione sincrona per inviare email.
    """
    mail_user = os.environ.get("MAIL_USERNAME")
    mail_pass = os.environ.get("MAIL_PASSWORD")
    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = os.environ.get("MAIL_PORT")

    if not all([mail_user, mail_pass, mail_server, mail_port]):
        print("⚠️ Config mail non completa")
        return

    try:
        mail_port = int(mail_port)
    except ValueError:
        print("⚠️ MAIL_PORT non è un numero valido")
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
        print(f"✅ Email inviata a {to_email}")
    except Exception as e:
        print(f"❌ Errore invio mail a {to_email}: {e}")

# ----------------- Wrapper asincrono -----------------
def send_email_async(to_email, subject, body):
    if ASYNC_EMAIL:
        threading.Thread(target=send_email, args=(to_email, subject, body)).start()
        print(f"📨 Invio asincrono a {to_email}")
    else:
        send_email(to_email,subject,body)
        print(f"📨 Invio sincrono a {to_email}")
