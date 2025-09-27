-- CLASSI
CREATE TABLE IF NOT EXISTS classi (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    ora TIME NOT NULL,
    max_posti INTEGER NOT NULL
);

-- UTENTI
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
    stato TEXT NOT NULL DEFAULT 'pending' -- pending | attivo | sospeso
);

-- PRENOTAZIONI
CREATE TABLE IF NOT EXISTS prenotazioni (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES utenti(id) ON DELETE CASCADE,
    classe_id INTEGER NOT NULL REFERENCES classi(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Un utente non può prenotare due volte la stessa classe
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_booking ON prenotazioni(user_id, classe_id);

-- Esempi di lezioni
INSERT INTO classi (data, ora, max_posti) VALUES ('2025-09-06', '19:00', 20);
INSERT INTO classi (data, ora, max_posti) VALUES ('2025-09-07', '19:00', 15);