from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

db = None  # verrà assegnato in __init__.py

def init_db_if_needed():
    # TABELLE
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
    # Inserimento lezioni iniziali
    result = db.execute(text("SELECT COUNT(*) AS n FROM classi")).fetchone()
    if result.n == 0:
        db.execute(text("INSERT INTO classi (data, ora, max_posti) VALUES ('2025-09-06', '19:00', 20)"))
        db.execute(text("INSERT INTO classi (data, ora, max_posti) VALUES ('2025-09-07', '19:00', 15)"))
    db.commit()
    print("✅ Database inizializzato!")
