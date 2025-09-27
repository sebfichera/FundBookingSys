from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import IntegrityError
import os
import smtplib
from email.message import EmailMessage

# ----------------- CONFIG -----------------
app = Flask(__name__)
app.secret_key = "bjj_super_secret_key"

MIN_ISCRITTI = 5

# ----------------- DATABASE -----------------
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("⚠️ DATABASE_URL non impostata!")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
db = scoped_session(sessionmaker(bind=engine))

def init_db_if_needed():
    """Crea le tabelle se non esistono e inserisce lezioni iniziali."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS classi (
            id SERIAL PRIMARY KEY,
            data DATE NOT NULL,
            ora TIME NOT NULL,
            max_posti INTEGER NOT NULL
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS utenti (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            cognome TEXT NOT NULL,
            data_nascita DATE NOT NULL,
            luogo_nascita TEXT NOT NULL,
            indirizzo TEXT NOT NULL,
            citta TEXT NOT NULL,
            comune TEXT NOT NULL,
            cap TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            telefono TEXT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            consenso_privacy BOOLEAN NOT NULL,
            stato TEXT NOT NULL DEFAULT 'pending'
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS prenotazioni (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES utenti(id) ON DELETE CASCADE,
            classe_id INTEGER NOT NULL REFERENCES classi(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_booking 
        ON prenotazioni(user_id, classe_id)
    """))
    # Inserisci lezioni iniziali solo se non ci sono
    result = db.execute(text("SELECT COUNT(*) AS n FROM classi")).fetchone()
    if result.n == 0:
        db.execute(text("INSERT INTO classi (data, ora, max_posti) VALUES ('2025-09-06', '19:00', 20)"))
        db.execute(text("INSERT INTO classi (data, ora, max_posti) VALUES ('2025-09-07', '19:00', 15)"))
    db.commit()
    print("✅ Database inizializzato!")

init_db_if_needed()

# ----------------- DECORATOR -----------------
def user_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Devi effettuare il login per prenotare.")
            return redirect(url_for("user_login"))
        if session.get("user_status") != "attivo":
            flash("Il tuo account non è ancora attivo. Attendi l’approvazione dell’admin.")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            flash("Devi effettuare il login come admin.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# ----------------- HOME -----------------
@app.route("/")
def home():
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

# ----------------- PRENOTAZIONE -----------------
@app.route("/prenota/<int:classe_id>", methods=["POST"])
@user_login_required
def prenota(classe_id):
    user_id = session["user_id"]
    count = db.execute(
        text("SELECT COUNT(*) AS n FROM prenotazioni WHERE classe_id=:cid"),
        {"cid": classe_id}
    ).fetchone().n
    row = db.execute(
        text("SELECT max_posti FROM classi WHERE id=:cid"),
        {"cid": classe_id}
    ).fetchone()
    if not row:
        flash("Classe inesistente.")
        return redirect(url_for("home"))
    max_posti = row.max_posti
    already = db.execute(
        text("SELECT 1 FROM prenotazioni WHERE user_id=:uid AND classe_id=:cid"),
        {"uid": user_id, "cid": classe_id}
    ).fetchone()
    if already:
        flash("Hai già una prenotazione per questa classe.")
        return redirect(url_for("home"))
    if count >= max_posti:
        flash("Classe piena!")
        return redirect(url_for("home"))
    try:
        db.execute(
            text("INSERT INTO prenotazioni (user_id, classe_id) VALUES (:uid, :cid)"),
            {"uid": user_id, "cid": classe_id}
        )
        db.commit()
        flash("✅ Prenotazione effettuata!")
    except IntegrityError:
        db.rollback()
        flash("Errore: prenotazione già esistente o dati non validi.")
    return redirect(url_for("home"))

# ----------------- REGISTRAZIONE UTENTE -----------------
@app.route("/register", methods=["GET", "POST"])
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
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

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
                    "consenso": int(consenso)
                }
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            flash("Email o username già esistenti.")
            return redirect(url_for("register"))

        # INVIO MAIL ADMIN
        admin_email = os.environ.get('ADMIN_EMAIL')
        if admin_email:
            try:
                msg = EmailMessage()
                msg['Subject'] = "Nuova registrazione in attesa"
                msg['From'] = os.environ.get('MAIL_USERNAME')
                msg['To'] = admin_email
                msg.set_content(
                    f"Nuovo utente registrato:\n\nNome: {nome}\nCognome: {cognome}\nUsername: {username}\nEmail: {email}"
                )
                with smtplib.SMTP(os.environ.get('MAIL_SERVER'), int(os.environ.get('MAIL_PORT'))) as server:
                    server.starttls()
                    server.login(os.environ.get('MAIL_USERNAME'), os.environ.get('MAIL_PASSWORD'))
                    server.send_message(msg)
            except Exception as e:
                print(f"Errore invio mail: {e}")

        flash("✅ Registrazione inviata! Attendi l’approvazione dell’admin.")
        return redirect(url_for("user_login"))

    return render_template("register.html")

# ----------------- USER LOGIN / LOGOUT -----------------
@app.route("/user/login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = db.execute(
            text("SELECT * FROM utenti WHERE username=:username"), {"username": username}
        ).fetchone()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Credenziali non valide.")
            return redirect(url_for("user_login"))
        if user.stato != "attivo":
            flash("Account non attivo. Attendi l’approvazione dell’admin.")
            return redirect(url_for("home"))
        session["user_id"] = user.id
        session["username"] = user.username
        session["user_status"] = user.stato
        flash(f"Benvenuto, {user.nome}!")
        return redirect(url_for("home"))
    return render_template("user_login.html")

@app.route("/user/logout")
def user_logout():
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("user_status", None)
    flash("Logout effettuato.")
    return redirect(url_for("home"))

# ----------------- ADMIN LOGIN / LOGOUT -----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "password123":
            session["admin"] = True
            flash("Login admin effettuato.")
            return redirect(url_for("admin"))
        else:
            flash("Credenziali errate!")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Logout admin effettuato.")
    return redirect(url_for("home"))

# ----------------- ADMIN DASHBOARD -----------------
@app.route("/admin")
@admin_required
def admin():
    classi = db.execute(text("SELECT * FROM classi ORDER BY data ASC, ora ASC")).fetchall()
    dati = []
    for c in classi:
        prenotati = db.execute(
            text("SELECT u.username FROM prenotazioni p JOIN utenti u ON u.id = p.user_id WHERE p.classe_id=:cid"),
            {"cid": c.id}
        ).fetchall()
        count = len(prenotati)
        stato = "ok"
        if count >= c.max_posti:
            stato = "piena"
        elif count < MIN_ISCRITTI:
            stato = "sotto_minimo"
        dati.append({
            "classe": c,
            "prenotati": [p.username for p in prenotati],
            "stato": stato,
            "count": count
        })
    return render_template("admin.html", dati=dati, min_iscritti=MIN_ISCRITTI)

# ----------------- ADMIN: GESTIONE CLASSI -----------------
@app.route("/admin/add", methods=["POST"])
@admin_required
def add_classe():
    data = request.form["data"]
    ora = request.form["ora"]
    max_posti = request.form["max_posti"]
    db.execute(
        text("INSERT INTO classi (data, ora, max_posti) VALUES (:data, :ora, :max_posti)"),
        {"data": data, "ora": ora, "max_posti": max_posti}
    )
    db.commit()
    flash("✅ Lezione aggiunta con successo!")
    return redirect(url_for("admin"))

@app.route("/admin/delete/<int:classe_id>")
@admin_required
def delete_classe(classe_id):
    db.execute(text("DELETE FROM prenotazioni WHERE classe_id=:cid"), {"cid": classe_id})
    db.execute(text("DELETE FROM classi WHERE id=:cid"), {"cid": classe_id})
    db.commit()
    flash("🗑️ Lezione eliminata con successo!")
    return redirect(url_for("admin"))

@app.route("/admin/edit/<int:classe_id>", methods=["GET", "POST"])
@admin_required
def edit_classe(classe_id):
    if request.method == "POST":
        data = request.form["data"]
        ora = request.form["ora"]
        max_posti = request.form["max_posti"]
        db.execute(
            text("UPDATE classi SET data=:data, ora=:ora, max_posti=:max_posti WHERE id=:cid"),
            {"data": data, "ora": ora, "max_posti": max_posti, "cid": classe_id}
        )
        db.commit()
        flash("✏️ Lezione modificata con successo!")
        return redirect(url_for("admin"))
    classe = db.execute(text("SELECT * FROM classi WHERE id=:cid"), {"cid": classe_id}).fetchone()
    return render_template("edit_classe.html", classe=classe)

# ----------------- ADMIN: GESTIONE UTENTI -----------------
@app.route("/admin/users")
@admin_required
def admin_users():
    users = db.execute(text("""
        SELECT id, nome, cognome, email, telefono, username, stato,
               data_nascita, luogo_nascita, indirizzo, citta, comune, cap
        FROM utenti
        ORDER BY stato DESC, cognome ASC, nome ASC
    """)).fetchall()
    return render_template("admin_users.html", users=users)

@app.route("/admin/users/<int:user_id>/approve")
@admin_required
def admin_users_approve(user_id):
    db.execute(text("UPDATE utenti SET stato='attivo' WHERE id=:uid"), {"uid": user_id})
    db.commit()
    user = db.execute(text("SELECT nome, cognome, email, username FROM utenti WHERE id=:uid"), {"uid": user_id}).fetchone()
    if user and user.email:
        try:
            msg = EmailMessage()
            msg['Subject'] = "Account approvato"
            msg['From'] = os.environ.get('MAIL_USERNAME')
            msg['To'] = user.email
            msg.set_content(
                f"Ciao {user.nome} {user.cognome},\n\n"
                f"Il tuo account (username: {user.username}) è stato approvato dall'admin.\n"
                "Ora puoi accedere e prenotare le lezioni.\n\nGrazie!"
            )
            with smtplib.SMTP(os.environ.get('MAIL_SERVER'), int(os.environ.get('MAIL_PORT'))) as server:
                server.starttls()
                server.login(os.environ.get('MAIL_USERNAME'), os.environ.get('MAIL_PASSWORD'))
                server.send_message(msg)
        except Exception as e:
            print(f"Errore invio mail all'utente: {e}")
    flash("✅ Utente approvato e notifica inviata via mail.")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/suspend")
@admin_required
def admin_users_suspend(user_id):
    db.execute(text("UPDATE utenti SET stato='sospeso' WHERE id=:uid"), {"uid": user_id})
    db.commit()
    flash("⏸️ Utente sospeso.")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/delete")
@admin_required
def admin_users_delete(user_id):
    db.execute(text("DELETE FROM prenotazioni WHERE user_id=:uid"), {"uid": user_id})
    db.execute(text("DELETE FROM utenti WHERE id=:uid"), {"uid": user_id})
    db.commit()
    flash("🗑️ Utente eliminato (e prenotazioni rimosse).")
    return redirect(url_for("admin_users"))

# ----------------- AVVIO -----------------
if __name__ == "__main__":
    app.run(debug=True)
