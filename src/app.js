'use strict';
/**
 * Secure Notes API -- Information Security lab, Work 1, variant 0.
 *
 * Endpoints
 *   POST /auth/login     authenticate, returns a JWT
 *   GET  /api/data       protected, returns the caller's notes
 *   POST /api/notes      protected, creates a note (own choice endpoint)
 *   GET  /api/notes/:id  protected, reads one note owned by the caller
 *   GET  /health         liveness probe (no data)
 */
const express = require('express');
const helmet = require('helmet');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const { openDb, q } = require('./db');
const {
  ValidationError, requireString, requireUsername, encodeForOutput,
} = require('./security');

const PORT = Number(process.env.PORT || 3000);
const BCRYPT_ROUNDS = 10;
const TOKEN_TTL = '1h';

/* ------------------------------------------------------------- JWT secret
 * The secret must come from the environment. A fallback is allowed only in
 * development so that `npm start` works out of the box; the process refuses to
 * start in production without a real secret.
 */
const JWT_SECRET = process.env.JWT_SECRET || 'dev-only-secret-do-not-use-in-production';
const IS_PROD = process.env.NODE_ENV === 'production';
if (IS_PROD && !process.env.JWT_SECRET) {
  console.error('FATAL: JWT_SECRET must be set when NODE_ENV=production');
  process.exit(1);
}

function createApp({ db = openDb(), secret = JWT_SECRET } = {}) {
  const app = express();

  app.disable('x-powered-by');
  app.use(helmet());
  app.use(express.json({ limit: '10kb' }));

  /* ------------------------------------------------------------ helpers */

  // A dummy hash used to keep the login path's timing constant when the
  // username does not exist. Without it, "no such user" returns much faster
  // than "wrong password", which leaks whether an account exists.
  const DUMMY_HASH = bcrypt.hashSync('dummy-password-for-timing', BCRYPT_ROUNDS);

  // Very small in-memory throttle for failed logins, per username. Enough to
  // blunt online guessing in a lab setting; a real deployment would use Redis.
  const failures = new Map();
  const MAX_FAILURES = 5;
  const FAILURE_WINDOW_MS = 15 * 60 * 1000;

  function noteFailure(username) {
    const now = Date.now();
    const rec = failures.get(username) || { count: 0, first: now };
    if (now - rec.first > FAILURE_WINDOW_MS) { rec.count = 0; rec.first = now; }
    rec.count += 1;
    failures.set(username, rec);
    return rec.count;
  }

  function isLockedOut(username) {
    const rec = failures.get(username);
    if (!rec) return false;
    if (Date.now() - rec.first > FAILURE_WINDOW_MS) { failures.delete(username); return false; }
    return rec.count >= MAX_FAILURES;
  }

  function issueToken(user) {
    return jwt.sign(
      { sub: String(user.id), username: user.username, role: user.role },
      secret,
      { algorithm: 'HS256', expiresIn: TOKEN_TTL, issuer: 'secure-notes-api' },
    );
  }

  /**
   * Authentication middleware.
   *
   * Verifies the signature and the registered claims (exp, iss) and then
   * reloads the user from the database, so that a token for a deleted account
   * stops working immediately.
   */
  function requireAuth(req, res, next) {
    const header = req.get('authorization') || '';
    const [scheme, token] = header.split(' ');
    if (!/^Bearer$/i.test(scheme || '') || !token) {
      return res.status(401).json({ error: 'missing bearer token' });
    }
    let payload;
    try {
      payload = jwt.verify(token, secret, { algorithms: ['HS256'], issuer: 'secure-notes-api' });
    } catch (err) {
      const reason = err.name === 'TokenExpiredError' ? 'token expired' : 'invalid token';
      return res.status(401).json({ error: reason });
    }
    const user = q.findUserById(db, Number(payload.sub));
    if (!user) return res.status(401).json({ error: 'invalid token' });
    req.user = user;
    return next();
  }

  /* ------------------------------------------------------------- routes */

  app.get('/health', (req, res) => res.json({ status: 'ok' }));

  // 1. Authentication
  app.post('/auth/login', (req, res) => {
    let username;
    try {
      username = requireUsername(req.body?.username);
    } catch {
      // Deliberately vague: do not tell an unauthenticated caller which part
      // of the credential pair was malformed.
      return res.status(401).json({ error: 'invalid credentials' });
    }

    const password = typeof req.body?.password === 'string' ? req.body.password : '';

    if (isLockedOut(username)) {
      return res.status(429).json({ error: 'too many failed attempts, try again later' });
    }

    const user = q.findUserByUsername(db, username);
    // Always run a bcrypt comparison, even when the user does not exist, so
    // that response time does not reveal account existence.
    const hash = user ? user.password_hash : DUMMY_HASH;
    const ok = bcrypt.compareSync(password, hash);

    if (!user || !ok) {
      noteFailure(username);
      return res.status(401).json({ error: 'invalid credentials' });
    }

    failures.delete(username);
    const token = issueToken(user);
    return res.json({
      token,
      token_type: 'Bearer',
      expires_in: 3600,
      user: encodeForOutput({ id: user.id, username: user.username, role: user.role }),
    });
  });

  // 2. Protected data (required endpoint)
  app.get('/api/data', requireAuth, (req, res) => {
    const rows = q.listNotesByOwner(db, req.user.id);
    res.json({ notes: encodeForOutput(rows) });
  });

  // 3. Own choice: create a note. Shows validation + storage + safe output.
  app.post('/api/notes', requireAuth, (req, res) => {
    let title, body;
    try {
      title = requireString(req.body?.title, 'title', { min: 1, max: 120 });
      body = requireString(req.body?.body, 'body', { min: 1, max: 2000 });
    } catch (err) {
      if (err instanceof ValidationError) return res.status(400).json({ error: err.message });
      throw err;
    }
    const info = q.createNote(db, req.user.id, title, body);
    const created = q.findNoteById(db, Number(info.lastInsertRowid), req.user.id);
    return res.status(201).json({ note: encodeForOutput(created) });
  });

  // 4. Read one note, scoped to the owner (prevents IDOR)
  app.get('/api/notes/:id', requireAuth, (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const note = q.findNoteById(db, id, req.user.id);
    if (!note) return res.status(404).json({ error: 'not found' });
    return res.json({ note: encodeForOutput(note) });
  });

  /* ------------------------------------------------------------ errors */
  app.use((req, res) => res.status(404).json({ error: 'not found' }));
  app.use((err, req, res, next) => {
    if (err instanceof SyntaxError && 'body' in err) {
      return res.status(400).json({ error: 'malformed JSON' });
    }
    if (err instanceof ValidationError) {
      return res.status(err.status || 400).json({ error: err.message });
    }
    // Never leak stack traces or driver errors to the client.
    console.error('unhandled error:', err.message);
    return res.status(500).json({ error: 'internal server error' });
  });

  return app;
}

module.exports = { createApp };

/* Start only when run directly, so tests can import createApp without
 * binding a port. */
if (require.main === module) {
  const app = createApp();
  app.listen(PORT, () => console.log(`secure-notes-api listening on http://127.0.0.1:${PORT}`));
}

