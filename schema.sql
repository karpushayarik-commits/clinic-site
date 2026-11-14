-- Структура бази даних клініки
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS services (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL DEFAULT '',
    price       INTEGER NOT NULL CHECK (price >= 0)
);

CREATE TABLE IF NOT EXISTS doctors (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
    experience INTEGER NOT NULL DEFAULT 0 CHECK (experience >= 0),
    bio        TEXT    NOT NULL DEFAULT '',
    education  TEXT    NOT NULL DEFAULT '',
    schedule   TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS appointments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    phone      TEXT    NOT NULL,
    doctor_id  INTEGER REFERENCES doctors(id) ON DELETE SET NULL,
    visit_date TEXT    NOT NULL,
    comment    TEXT    NOT NULL DEFAULT '',
    status     TEXT    NOT NULL DEFAULT 'нова',
    created    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
