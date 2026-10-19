'use strict';
/**
 * Database layer.
 *
 * Uses the built-in `node:sqlite` module (Node >= 22.5), so the project has no
 * native build step. Every query in this project goes through a prepared
 * statement with bound parameters -- see the note in the security section of
 * the README.
 */
const path = require('node:path');
const fs = require('node:fs');
const { DatabaseSync } = require('node:sqlite');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, '..', 'data', 'app.db');

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id   INTEGER NOT NULL REFERENCES users(id),
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE INDEX IF NOT EXISTS idx_notes_owner ON notes(owner_id);
`;

function openDb(filename = DB_PATH) {
  if (filename !== ':memory:') {
    // The path is configuration, never request input, so this is a false
    // positive for the non-literal-filename rule.
    // eslint-disable-next-line security/detect-non-literal-fs-filename
    fs.mkdirSync(path.dirname(filename), { recursive: true });
  }
  const db = new DatabaseSync(filename);
  db.exec('PRAGMA foreign_keys = ON;');
  db.exec(SCHEMA);
  return db;
}

/* ---------------------------------------------------------------- queries
 * All of these are prepared statements. The SQL text is a constant in this
 * file; the only thing that varies is the bound parameters. This is what makes
 * SQL injection impossible: user input never becomes part of the SQL text.
 */
const q = {
  findUserByUsername(db, username) {
    return db.prepare('SELECT id, username, password_hash, role FROM users WHERE username = ?')
             .get(username);
  },
  findUserById(db, id) {
    return db.prepare('SELECT id, username, role FROM users WHERE id = ?').get(id);
  },
  createUser(db, username, passwordHash, role = 'user') {
    return db.prepare('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)')
             .run(username, passwordHash, role);
  },
  listNotesByOwner(db, ownerId) {
    return db.prepare('SELECT id, owner_id, title, body, created_at FROM notes WHERE owner_id = ? ORDER BY id DESC')
             .all(ownerId);
  },
  createNote(db, ownerId, title, body) {
    return db.prepare('INSERT INTO notes (owner_id, title, body) VALUES (?, ?, ?)')
             .run(ownerId, title, body);
  },
  findNoteById(db, id, ownerId) {
    return db.prepare('SELECT id, owner_id, title, body, created_at FROM notes WHERE id = ? AND owner_id = ?')
             .get(id, ownerId);
  },
  countUsers(db) {
    return db.prepare('SELECT COUNT(*) AS n FROM users').get().n;
  },
};

module.exports = { openDb, q, DB_PATH };

