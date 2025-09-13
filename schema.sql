-- CLASSI
CREATE TABLE IF NOT EXISTS classi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data DATE NOT NULL,
    ora TIME NOT NULL,
    max_posti INTEGER NOT NULL
);

-- UTENTI
CREATE TABLE IF NOT EXISTS utenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    stato TEXT NOT NULL DEFAULT 'pending' -- pending | attivo | sospeso
);

-- PRENOTAZIONI
CREATE TABLE IF NOT EXISTS prenotazioni (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    classe_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES utenti(id),
    FOREIGN KEY (classe_id) REFERENCES classi(id)
);

-- Un utente non può prenotare due volte la stessa classe
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_booking ON prenotazioni(user_id, classe_id);

-- Esempi di lezioni
INSERT INTO classi (data, ora, max_posti) VALUES ('2025-09-06', '19:00', 20);
INSERT INTO classi (data, ora, max_posti) VALUES ('2025-09-07', '19:00', 15);