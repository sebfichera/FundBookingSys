from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "bjj_super_secret_key"

DB_FILE = "prenotazioni.db"
SCHEMA_FILE = "schema.sql"
MIN_ISCRITTI = 5

# ----------------- DB -----------------
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_if_needed():
    if not os.path.exists(DB_FILE):
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema = f.read()
        conn = sqlite3.connect(DB_FILE)
        conn.executescript(schema)
        conn.commit()
        conn.close()
        print("✅ Database creato e inizializzato!")

init_db_if_needed()

# ----------------- Decorators -----------------
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
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# ----------------- HOME -----------------
@app.route("/")
def home():
    db = get_db()
    classi = db.execute("SELECT * FROM classi ORDER BY data ASC, ora ASC").fetchall()
    prenotazioni_count = {}
    for c in classi:
        count = db.execute(
            "SELECT COUNT(*) AS n FROM prenotazioni WHERE classe_id=?",
            (c["id"],)
        ).fetchone()["n"]
        prenotazioni_count[c["id"]] = count

    return render_template(
        "home.html",
        classi=classi,
        prenotazioni=prenotazioni_count,
        user_id=session.get("user_id"),
        user_status=session.get("user_status"),
    )

# ----------------- PRENOTAZIONE -----------------
@app.route("/prenota/<int:classe_id>", methods=["POST"])
@user_login_required
def prenota(classe_id):
    user_id = session["user_id"]
    db = get_db()

    # posti occupati e max
    count = db.execute("SELECT COUNT(*) AS n FROM prenotazioni WHERE classe_id=?",
                       (classe_id,)).fetchone()["n"]
    row = db.execute("SELECT max_posti FROM classi WHERE id=?", (classe_id,)).fetchone()
    if not row:
        flash("Classe inesistente.")
        return redirect(url_for("home"))
    max_posti = row["max_posti"]

    # già prenotato?
    already = db.execute(
        "SELECT 1 FROM prenotazioni WHERE user_id=? AND classe_id=?",
        (user_id, classe_id)
    ).fetchone()
    if already:
        flash("Hai già una prenotazione per questa classe.")
        return redirect(url_for("home"))

    if count >= max_posti:
        flash("Classe piena!")
        return redirect(url_for("home"))

    db.execute(
        "INSERT INTO prenotazioni (user_id, classe_id) VALUES (?, ?)",
        (user_id, classe_id)
    )
    db.commit()
    flash("✅ Prenotazione effettuata!")
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

        db = get_db()
        try:
            db.execute("""
                INSERT INTO utenti (
                    nome, cognome, data_nascita, luogo_nascita, indirizzo, citta, comune, cap,
                    email, telefono, username, password_hash, consenso_privacy, stato
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'pending')
            """, (nome, cognome, data_nascita, luogo_nascita, indirizzo, citta, comune, cap,
                  email, telefono, username, password_hash, int(consenso)))
            db.commit()
        except sqlite3.IntegrityError:
            flash("Email o username già esistenti.")
            return redirect(url_for("register"))

        flash("✅ Registrazione inviata! Attendi l’approvazione dell’admin.")
        return redirect(url_for("user_login"))

    return render_template("register.html")

# ----------------- USER LOGIN / LOGOUT -----------------
@app.route("/user/login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM utenti WHERE username=?",
            (username,)
        ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Credenziali non valide.")
            return redirect(url_for("user_login"))

        if user["stato"] != "attivo":
            flash("Account non attivo. Attendi l’approvazione dell’admin.")
            return redirect(url_for("user_login"))

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["user_status"] = user["stato"]
        flash(f"Benvenuto, {user['nome']}!")
        return redirect(url_for("home"))

    return render_template("user_login.html")

@app.route("/user/logout")
def user_logout():
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("user_status", None)
    flash("Logout effettuato.")
    return redirect(url_for("home"))

# ----------------- ADMIN LOGIN / LOGOUT (già esistenti) -----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    # login admin semplice hardcoded
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "password123":
            session["admin"] = True
            return redirect(url_for("admin"))
        else:
            flash("Credenziali errate!")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# ----------------- ADMIN PAGINE ESISTENTI -----------------
@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    classi = db.execute("SELECT * FROM classi ORDER BY data ASC, ora ASC").fetchall()
    dati = []
    for c in classi:
        prenotati = db.execute("""
            SELECT u.username
            FROM prenotazioni p
            JOIN utenti u ON u.id = p.user_id
            WHERE p.classe_id=?
        """, (c["id"],)).fetchall()
        count = len(prenotati)
        stato = "ok"
        if count >= c["max_posti"]:
            stato = "piena"
        elif count < MIN_ISCRITTI:
            stato = "sotto_minimo"
        dati.append({
            "classe": c,
            "prenotati": [p["username"] for p in prenotati],
            "stato": stato,
            "count": count
        })
    return render_template("admin.html", dati=dati, min_iscritti=MIN_ISCRITTI)

@app.route("/admin/add", methods=["POST"])
@admin_required
def add_classe():
    data = request.form["data"]
    ora = request.form["ora"]
    max_posti = request.form["max_posti"]
    db = get_db()
    db.execute("INSERT INTO classi (data, ora, max_posti) VALUES (?,?,?)", (data, ora, max_posti))
    db.commit()
    flash("✅ Lezione aggiunta con successo!")
    return redirect(url_for("admin"))

@app.route("/admin/delete/<int:classe_id>")
@admin_required
def delete_classe(classe_id):
    db = get_db()
    db.execute("DELETE FROM prenotazioni WHERE classe_id=?", (classe_id,))
    db.execute("DELETE FROM classi WHERE id=?", (classe_id,))
    db.commit()
    flash("🗑️ Lezione eliminata con successo!")
    return redirect(url_for("admin"))

@app.route("/admin/edit/<int:classe_id>", methods=["GET", "POST"])
@admin_required
def edit_classe(classe_id):
    db = get_db()
    if request.method == "POST":
        data = request.form["data"]
        ora = request.form["ora"]
        max_posti = request.form["max_posti"]
        db.execute("UPDATE classi SET data=?, ora=?, max_posti=? WHERE id=?",
                   (data, ora, max_posti, classe_id))
        db.commit()
        flash("✏️ Lezione modificata con successo!")
        return redirect(url_for("admin"))
    classe = db.execute("SELECT * FROM classi WHERE id=?", (classe_id,)).fetchone()
    return render_template("edit_classe.html", classe=classe)

# ----------------- ADMIN: GESTIONE UTENTI -----------------
@app.route("/admin/users")
@admin_required
def admin_users():
    db = get_db()
    users = db.execute("""
        SELECT id, nome, cognome, email, telefono, username, stato,
               data_nascita, luogo_nascita, indirizzo, citta, comune, cap
        FROM utenti
        ORDER BY stato DESC, cognome ASC, nome ASC
    """).fetchall()
    return render_template("admin_users.html", users=users)

@app.route("/admin/users/<int:user_id>/approve")
@admin_required
def admin_users_approve(user_id):
    db = get_db()
    db.execute("UPDATE utenti SET stato='attivo' WHERE id=?", (user_id,))
    db.commit()
    flash("✅ Utente approvato.")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/suspend")
@admin_required
def admin_users_suspend(user_id):
    db = get_db()
    db.execute("UPDATE utenti SET stato='sospeso' WHERE id=?", (user_id,))
    db.commit()
    flash("⏸️ Utente sospeso.")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/delete")
@admin_required
def admin_users_delete(user_id):
    db = get_db()
    db.execute("DELETE FROM prenotazioni WHERE user_id=?", (user_id,))
    db.execute("DELETE FROM utenti WHERE id=?", (user_id,))
    db.commit()
    flash("🗑️ Utente eliminato (e prenotazioni rimosse).")
    return redirect(url_for("admin_users"))

# ----------------- AVVIO -----------------
if __name__ == "__main__":
    app.run(debug=True)
