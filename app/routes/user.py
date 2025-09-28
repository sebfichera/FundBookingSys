import os
from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from ..models import db
from ..utils import hash_password, verify_password, send_email
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

user_bp = Blueprint("user_bp", __name__)

# ----------------- HOME -----------------
@user_bp.route("/")
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
                send_email(
                    admin_email,
                    "Nuova registrazione in attesa",
                    f"Nuovo utente registrato:\n\nNome: {nome}\nCognome: {cognome}\nUsername: {username}\nEmail: {email}",
                    async_send=True  # invio in thread separato
                )
                print("💡 Mail inviata all'admin")
        except Exception as e:
            print("⚠️ Errore invio mail admin:", e)

        flash("✅ Registrazione inviata! Attendi l’approvazione dell’admin.")
        return redirect(url_for("user_bp.user_login"))

    return render_template("register.html")

# ----------------- LOGIN UTENTE -----------------
@user_bp.route("/user/login", methods=["GET", "POST"])
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
