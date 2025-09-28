from flask import Blueprint, session, redirect, url_for, flash
from ..models import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

prenotazioni_bp = Blueprint("prenotazioni_bp", __name__, url_prefix="/prenota")  # aggiunto url_prefix

# ----------------- DECORATOR LOGIN UTENTE -----------------
def user_login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Devi effettuare il login per prenotare.")
            return redirect(url_for("user_bp.user_login"))
        if session.get("user_status") != "attivo":
            flash("Il tuo account non è ancora attivo. Attendi l’approvazione dell’admin.")
            return redirect(url_for("user_bp.user_login"))
        return f(*args, **kwargs)
    return wrapper

# ----------------- PRENOTA CLASSE -----------------
@prenotazioni_bp.route("/<int:classe_id>", methods=["POST"])
@user_login_required
def prenota(classe_id):
    user_id = session["user_id"]

    # Verifica esistenza classe
    row = db.execute(
        text("SELECT max_posti FROM classi WHERE id=:cid"), {"cid": classe_id}
    ).fetchone()
    if not row:
        flash("Classe inesistente.")
        return redirect(url_for("user_bp.home"))

    max_posti = row.max_posti

    # Conta prenotazioni attuali
    count = db.execute(
        text("SELECT COUNT(*) AS n FROM prenotazioni WHERE classe_id=:cid"), {"cid": classe_id}
    ).fetchone().n

    if count >= max_posti:
        flash("Classe piena!")
        return redirect(url_for("user_bp.home"))

    # Controllo prenotazione già esistente
    already = db.execute(
        text("SELECT 1 FROM prenotazioni WHERE user_id=:uid AND classe_id=:cid"),
        {"uid": user_id, "cid": classe_id}
    ).fetchone()
    if already:
        flash("Hai già una prenotazione per questa classe.")
        return redirect(url_for("user_bp.home"))

    # Inserimento prenotazione
    try:
        db.execute(
            text("INSERT INTO prenotazioni (user_id, classe_id) VALUES (:uid,:cid)"),
            {"uid": user_id, "cid": classe_id}
        )
        db.commit()
        flash("✅ Prenotazione effettuata!")
    except IntegrityError:
        db.rollback()
        flash("Errore: prenotazione già esistente o dati non validi.")

    return redirect(url_for("user_bp.home"))
