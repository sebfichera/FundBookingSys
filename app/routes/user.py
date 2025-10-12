import os
from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from ..models import db
from ..utils import hash_password, verify_password, send_email_async
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import text
import secrets
import traceback
from datetime import datetime, timedelta, timezone
from . import db
from functools import wraps

user_bp = Blueprint("user_bp", __name__)

# ----------------- DECORATORE GESTIONE ERRORI DB -----------------
def handle_db_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as e:
            db.rollback()
            print("❌ Errore DB:", e)
            traceback.print_exc()
            flash("⚠️ Problema di connessione al database. Riprova più tardi.", "danger")
            return redirect(url_for("user_bp.home"))
        except Exception as e:
            print("❌ Errore generico:", e)
            traceback.print_exc()
            flash("Si è verificato un errore. Controlla i log.", "danger")
            return redirect(url_for("user_bp.home"))
    return wrapper

# ----------------- HOME -----------------
@user_bp.route("/")
@handle_db_errors
def home():
    print("🚀 Home route chiamata")
    classi = db.execute(text("SELECT * FROM classi ORDER BY data ASC, ora ASC")).fetchall()
    prenotazioni_count = {}
    for c in classi:
        count = db.execute(
            text("SELECT COUNT(*) AS n FROM prenotazioni WHERE classe_id=:cid"),
            {"cid": c.id}
        ).fetchone().n
        prenotazioni_count[c.id] = count
    return render_template(
        "home.html",
        classi=classi,
        prenotazioni=prenotazioni_count,
        user_id=session.get("user_id"),
        user_status=session.get("user_status")
    )

# ----------------- REGISTRAZIONE -----------------
@user_bp.route("/user/register", methods=["GET", "POST"])
@handle_db_errors
def register():
    if request.method == "POST":

        print("💡 Inizio registrazione")  # debug iniziale

        nome = request.form["nome"].strip()
        cognome = request.form["cognome"].strip()
        data_nascita = request.form["data_nascita"]
        luogo_nascita = request.form["luogo_nascita"].strip()
        indirizzo = request.form["indirizzo"].strip()
        citta = request.form["citta"].strip()
        comune = request.form["comune"].strip()
        cap = request.form["cap"].strip()
        email = request.form["email"].strip().lower()
        telefono = request.form["telefono"].strip()
        username = request.form["username"].strip()
        password = request.form["password"]
        consenso = request.form.get("consenso_privacy") == "on"

        print("💡 Dati letti:", nome, cognome, email, username, consenso)

        if not consenso:
            flash("Devi acconsentire al trattamento dei dati per proseguire.")
            return redirect(url_for("user_bp.register"))

        password_hash = hash_password(password)

        print("💡 Password hash generata")

        try:
            db.execute(
                text("""
                    INSERT INTO utenti (
                        nome, cognome, data_nascita, luogo_nascita, indirizzo, citta, comune, cap,
                        email, telefono, username, password_hash, consenso_privacy, stato
                    ) VALUES (
                        :nome, :cognome, :data_nascita, :luogo_nascita, :indirizzo, :citta, :comune, :cap,
                        :email, :telefono, :username, :password_hash, :consenso, 'pending'
                    )
                """),
                {
                    "nome": nome,
                    "cognome": cognome,
                    "data_nascita": data_nascita,
                    "luogo_nascita": luogo_nascita,
                    "indirizzo": indirizzo,
                    "citta": citta,
                    "comune": comune,
                    "cap": cap,
                    "email": email,
                    "telefono": telefono,
                    "username": username,
                    "password_hash": password_hash,
                    "consenso": consenso
                }
            )
            db.commit()

            print("💡 Utente inserito nel DB")

        except IntegrityError:
            db.rollback()

            print("⚠️ IntegrityError:", e)

            flash("Email o username già esistenti.") 
            return redirect(url_for("user_bp.register"))
        except Exception as e:
            db.rollback()
            print("❌ Errore generico durante registrazione:", e)
            flash("Errore durante la registrazione. Contatta l'admin.")
            return redirect(url_for("user_bp.register"))
        
        # Mail admin
        try:
            admin_email = os.environ.get("ADMIN_EMAIL")
            if admin_email:
                send_email_async(
                    admin_email,
                    "Nuova registrazione in attesa",
                    f"Nuovo utente registrato:\n\nNome: {nome}\nCognome: {cognome}\nUsername: {username}\nEmail: {email}"
                )
                print("💡 Mail inviata all'admin")
        except Exception as e:
            print("⚠️ Errore invio mail admin:", e)

        flash("✅ Registrazione inviata! Attendi l’approvazione dell’admin.")
        return redirect(url_for("user_bp.user_login"))

    return render_template("register.html")

# ----------------- LOGIN UTENTE -----------------
@user_bp.route("/user/login", methods=["GET", "POST"])
@handle_db_errors
def user_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = db.execute(
            text("SELECT * FROM utenti WHERE username=:username"),
            {"username": username}
        ).fetchone()

        if not user or not verify_password(user.password_hash, password):
            flash("Credenziali non valide.")
            return redirect(url_for("user_bp.user_login"))

        if user.stato != "attivo":
            flash("Account non attivo. Attendi l’approvazione dell’admin.")
            return redirect(url_for("user_bp.user_login"))

        session["user_id"] = user.id
        session["username"] = user.username
        session["user_status"] = user.stato
        flash(f"Benvenuto, {user.nome}!")
        return redirect(url_for("user_bp.home"))

    return render_template("user_login.html")

# ----------------- LOGOUT UTENTE -----------------
@user_bp.route("/user/logout")
def user_logout():
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("user_status", None)
    flash("Logout effettuato.")
    return redirect(url_for("user_bp.home"))

# ----------------- RECUPERO USERNAME UTENTE -----------------
@user_bp.route("/recover_username", methods=["GET", "POST"])
@handle_db_errors
def recover_username():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = db.execute(text("SELECT username FROM utenti WHERE email=:email"), {"email": email}).fetchone()

        if not user:
            flash("Nessun utente trovato con questa email.")
            return redirect(url_for("user_bp.recover_username"))

        # Invio mail
        send_email_async(
            email,
            "Recupero username",
            f"Ciao! Il tuo username è: {user.username}"
        )
        flash("✅ Ti abbiamo inviato una mail con il tuo username.")
        return redirect(url_for("user_bp.user_login"))

    return render_template("recover_username.html")

# ----------------- RESET PASSWORD UTENTE (GENERA TOKEN) -----------------
@user_bp.route("/recover_password", methods=["GET", "POST"])
@handle_db_errors
def recover_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        try:
            user = db.execute(
                text("SELECT id, username, email FROM utenti WHERE email = :email"),
                {"email": email}
            ).fetchone()

            if not user:
                flash("Nessun account trovato con questa email.")
                return redirect(url_for("user_bp.recover_password"))

            # genera token + scadenza (1 ora)
            token = secrets.token_urlsafe(32)
            expiry = datetime.now(timezone.utc) + timedelta(hours=1)

            # salva nel DB
            db.execute(
                text("UPDATE utenti SET reset_token = :token, reset_token_expiry = :expiry WHERE id = :id"),
                {"token": token, "expiry": expiry, "id": user.id}
            )
            db.commit()

            # link assoluto
            reset_link = url_for("user_bp.reset_password", token=token, _external=True)

            # invio mail (non deve far fallire la route)
            try:
                send_email_async(
                    user.email,
                    "Reimposta la tua password",
                    f"Ciao {user.username},\n\nPer reimpostare la password clicca qui:\n{reset_link}\n\nIl link scade tra 1 ora."
                )
            except Exception as e:
                print("❌ Errore invio mail (recover_password):", e)
                traceback.print_exc()  # utile per debug, controlla i log

            flash("Se l'email esiste, abbiamo inviato il link per reimpostare la password.")
            return redirect(url_for("user_bp.user_login"))

        except Exception as e:
            print("❌ Errore in recover_password:", e)
            traceback.print_exc()
            flash("Si è verificato un errore. Controlla i log.")
            return redirect(url_for("user_bp.recover_password"))

    return render_template("recover_password.html")

# ----------------- RESET PASSWORD UTENTE (CREA NUOVA PASSWORD) -----------------
@user_bp.route("/reset_password/<token>", methods=["GET", "POST"])
@handle_db_errors
def reset_password(token):
    try:
        user = db.execute(
            text("SELECT id, reset_token_expiry FROM utenti WHERE reset_token = :token"),
            {"token": token}
        ).fetchone()

        if not user:
            flash("Token non valido o già usato.")
            return redirect(url_for("user_bp.recover_password"))

        expiry = user.reset_token_expiry
        now = datetime.now(timezone.utc)

        # gestione naive/aware
        if expiry is None:
            flash("Token non valido.")
            return redirect(url_for("user_bp.recover_password"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if now > expiry:
            flash("Il link per reimpostare la password è scaduto.")
            return redirect(url_for("user_bp.recover_password"))

        if request.method == "POST":
            new_pw = request.form.get("password", "")
            if len(new_pw) < 6:
                flash("La password deve essere lunga almeno 6 caratteri.")
                return redirect(url_for("user_bp.reset_password", token=token))

            pw_hash = hash_password(new_pw)
            db.execute(
                text("UPDATE utenti SET password_hash = :pw, reset_token = NULL, reset_token_expiry = NULL WHERE id = :id"),
                {"pw": pw_hash, "id": user.id}
            )
            db.commit()
            flash("✅ Password aggiornata. Ora puoi effettuare il login.")
            return redirect(url_for("user_bp.user_login"))

        return render_template("reset_password.html", token=token)

    except Exception as e:
        print("❌ Errore in reset_password:", e)
        traceback.print_exc()
        flash("Si è verificato un errore. Controlla i log.")
        return redirect(url_for("user_bp.recover_password"))
