import os
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
import threading

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
def send_email(to_email: str, subject: str, body: str, async_send: bool = True):
    """
    Invia un'email. 
    Se async_send=True, viene inviato in un thread separato (non blocca Flask).
    """
    mail_user = os.environ.get("MAIL_USERNAME")
    mail_pass = os.environ.get("MAIL_PASSWORD")
    mail_server = os.environ.get("MAIL_SERVER")
    mail_port_str = os.environ.get("MAIL_PORT")
    use_tls = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    use_ssl = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"

    if not all([mail_user, mail_pass, mail_server, mail_port_str]):
        print("⚠️ Config mail non completa")
        return

    try:
        mail_port = int(mail_port_str)
    except ValueError:
        print("⚠️ MAIL_PORT non è un numero valido")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = mail_user
    msg['To'] = to_email
    msg.set_content(body)

    def _send():
        try:
            if use_ssl:
                with smtplib.SMTP_SSL(mail_server, mail_port) as server:
                    server.login(mail_user, mail_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(mail_server, mail_port) as server:
                    if use_tls:
                        server.starttls()
                    server.login(mail_user, mail_pass)
                    server.send_message(msg)
            print(f"📧 Mail inviata a {to_email}")
        except Exception as e:
            print(f"Errore invio mail a {to_email}: {e}")

    if async_send:
        threading.Thread(target=_send, daemon=True).start()
    else:
        _send()
