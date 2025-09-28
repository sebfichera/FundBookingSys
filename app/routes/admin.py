import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..models import db
from ..utils import send_email
from sqlalchemy import text

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")  # url_prefix per tutte le route admin

MIN_ISCRITTI = 5  # minimo iscritti per classe

# ----------------- DECORATOR ADMIN -----------------
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            flash("Devi effettuare il login come admin.")
            return redirect(url_for("user_bp.user_login"))
        return f(*args, **kwargs)
    return wrapper

# ----------------- LOGIN ADMIN -----------------
@admin_bp.route("/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        # Qui controlla che sia admin (puoi usare una colonna 'is_admin' oppure controllo sullo username)
        if username == os.environ.get("ADMIN_USERNAME") and password == os.environ.get("ADMIN_PASSWORD"):
            session["admin"] = True
            flash("✅ Login admin effettuato!")
            return redirect(url_for("admin_bp.dashboard"))
        else:
            flash("Credenziali admin non valide.")
            return redirect(url_for("admin_bp.admin_login"))

    return render_template("login.html")  # template login admin

# ----------------- DASHBOARD -----------------
@admin_bp.route("/")
@admin_required
def dashboard():
    try:
        classi = db.execute(
            text("SELECT * FROM classi ORDER BY data ASC, ora ASC")
        ).fetchall()

        dati = []
        for c in classi:
            # accedi come dict, non come attributo
            prenotati = db.execute(
                text("""
                    SELECT u.username 
                    FROM prenotazioni p 
                    JOIN utenti u ON u.id = p.user_id 
                    WHERE p.classe_id = :cid
                """),
                {"cid": c["id"]}
            ).fetchall()

            count = len(prenotati)
            stato = "ok"
            if count >= c["max_posti"]:
                stato = "piena"
            elif count < MIN_ISCRITTI:
                stato = "sotto_minimo"

            dati.append({
                "classe": c,  # puoi passare Row direttamente al template
                "prenotati": [p.username for p in prenotati],
                "stato": stato,
                "count": count
            })

        return render_template("admin.html", dati=dati, min_iscritti=MIN_ISCRITTI)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Errore in dashboard: {e}", 500

# ----------------- GESTIONE CLASSI -----------------
@admin_bp.route("/add", methods=["POST"])
@admin_required
def add_classe():
    data = request.form["data"]
    ora = request.form["ora"]
    max_posti = request.form["max_posti"]
    db.execute(text("INSERT INTO classi (data, ora, max_posti) VALUES (:data,:ora,:max_posti)"),
               {"data": data, "ora": ora, "max_posti": max_posti})
    db.commit()
    flash("✅ Lezione aggiunta con successo!")
    return redirect(url_for("admin_bp.dashboard"))

@admin_bp.route("/delete/<int:classe_id>")
@admin_required
def delete_classe(classe_id):
    db.execute(text("DELETE FROM prenotazioni WHERE classe_id=:cid"), {"cid": classe_id})
    db.execute(text("DELETE FROM classi WHERE id=:cid"), {"cid": classe_id})
    db.commit()
    flash("🗑️ Lezione eliminata con successo!")
    return redirect(url_for("admin_bp.dashboard"))

@admin_bp.route("/edit/<int:classe_id>", methods=["GET", "POST"])
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
        return redirect(url_for("admin_bp.dashboard"))

    classe = db.execute(text("SELECT * FROM classi WHERE id=:cid"), {"cid": classe_id}).fetchone()
    return render_template("edit_classe.html", classe=classe)

# ----------------- GESTIONE UTENTI -----------------
@admin_bp.route("/users")
@admin_required
def admin_users():
    users = db.execute(text("""
        SELECT id,nome,cognome,email,telefono,username,stato,
               data_nascita,luogo_nascita,indirizzo,citta,comune,cap
        FROM utenti
        ORDER BY stato DESC, cognome ASC, nome ASC
    """)).fetchall()
    return render_template("admin_users.html", users=users)

@admin_bp.route("/users/<int:user_id>/approve")
@admin_required
def admin_users_approve(user_id):
    db.execute(text("UPDATE utenti SET stato='attivo' WHERE id=:uid"), {"uid": user_id})
    db.commit()
    user = db.execute(text("SELECT nome,cognome,email,username FROM utenti WHERE id=:uid"), {"uid": user_id}).fetchone()
    if user and user.email:
        send_email(
            user.email,
            "Account approvato",
            f"Ciao {user.nome} {user.cognome},\n\nIl tuo account (username: {user.username}) è stato approvato dall'admin.\nOra puoi accedere e prenotare le lezioni.\n\nGrazie!",
            async_send=True  # invio in thread separato
        )
    flash("✅ Utente approvato e notifica inviata via mail.")
    return redirect(url_for("admin_bp.admin_users"))

@admin_bp.route("/users/<int:user_id>/suspend")
@admin_required
def admin_users_suspend(user_id):
    db.execute(text("UPDATE utenti SET stato='sospeso' WHERE id=:uid"), {"uid": user_id})
    db.commit()
    flash("⏸️ Utente sospeso.")
    return redirect(url_for("admin_bp.admin_users"))

@admin_bp.route("/users/<int:user_id>/delete")
@admin_required
def admin_users_delete(user_id):
    db.execute(text("DELETE FROM prenotazioni WHERE user_id=:uid"), {"uid": user_id})
    db.execute(text("DELETE FROM utenti WHERE id=:uid"), {"uid": user_id})
    db.commit()
    flash("🗑️ Utente eliminato (e prenotazioni rimosse).")
    return redirect(url_for("admin_bp.admin_users"))
