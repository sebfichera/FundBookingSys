from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from ..models import db
from ..utils import hash_password, verify_password, send_email
from sqlalchemy.exc import IntegrityError

user_bp = Blueprint("user_bp", __name__)

@user_bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
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

        if not consenso:
            flash("Devi acconsentire al trattamento dei dati per proseguire.")
            return redirect(url_for("user_bp.register"))

        password_hash = hash_password(password)

        try:
            db.execute("""
                INSERT INTO utenti (nome,cognome,data_nascita,luogo_nascita,indirizzo,citta,comune,cap,
                    email,telefono,username,password_hash,consenso_privacy,stato)
                VALUES (:nome,:cognome,:data_nascita,:luogo_nascita,:indirizzo,:citta,:comune,:cap,
                        :email,:telefono,:username,:password_hash,:consenso,'pending')
            """, {"nome":nome,"cognome":cognome,"data_nascita":data_nascita,
                  "luogo_nascita":luogo_nascita,"indirizzo":indirizzo,"citta":citta,
                  "comune":comune,"cap":cap,"email":email,"telefono":telefono,
                  "username":username,"password_hash":password_hash,"consenso":int(consenso)})
            db.commit()
        except IntegrityError:
            db.rollback()
            flash("Email o username già esistenti.") 
            return redirect(url_for("user_bp.register"))

        # Mail admin
        admin_email = os.environ.get("ADMIN_EMAIL")
        if admin_email:
            send_email(admin_email, "Nuova registrazione in attesa",
                f"Nuovo utente registrato:\n\nNome: {nome}\nCognome: {cognome}\nUsername: {username}\nEmail: {email}")

        flash("✅ Registrazione inviata! Attendi l’approvazione dell’admin.")
        return redirect(url_for("user_bp.user_login"))

    return render_template("register.html")

@user_bp.route("/user/login", methods=["GET","POST"])
def user_login():
    if request.method=="POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = db.execute("SELECT * FROM utenti WHERE username=:username", {"username":username}).fetchone()
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
        return redirect("/")

    return render_template("user_login.html")

@user_bp.route("/user/logout")
def user_logout():
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("user_status", None)
    flash("Logout effettuato.")
    return redirect("/")
