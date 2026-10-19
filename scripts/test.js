'use strict';
/**
 * Automated test suite for the API.
 *
 * Starts the app on an ephemeral port against an in-memory database, so it can
 * run in CI without touching the file system. Every check maps to a security
 * property claimed in the README.
 *
 * Run with: npm test
 */
const assert = require('node:assert');
const bcrypt = require('bcryptjs');
const { createApp } = require('../src/app');
const { openDb, q } = require('../src/db');

const results = [];
let server;
let base;

function record(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  -- ' + detail : ''}`);
}

async function check(name, fn) {
  try {
    await fn();
    record(name, true);
  } catch (err) {
    record(name, false, err.message);
  }
}

const api = (path, opts = {}) =>
  fetch(base + path, {
    ...opts,
    headers: { 'content-type': 'application/json', ...(opts.headers || {}) },
  });

async function main() {
  const db = openDb(':memory:');
  q.createUser(db, 'alice', bcrypt.hashSync('Alice#2026pass', 10), 'user');
  q.createUser(db, 'bob', bcrypt.hashSync('Bob#2026password', 10), 'user');

  const app = createApp({ db, secret: 'test-secret' });
  await new Promise((resolve) => {
    server = app.listen(0, '127.0.0.1', resolve);
  });
  base = `http://127.0.0.1:${server.address().port}`;

  let aliceToken;
  let bobToken;
  let noteId;

  /* ---------------------------------------------------- authentication */

  await check('login with valid credentials returns a token', async () => {
    const r = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: 'alice', password: 'Alice#2026pass' }),
    });
    assert.strictEqual(r.status, 200);
    const body = await r.json();
    assert.ok(body.token && body.token.split('.').length === 3, 'expected a three-part JWT');
    assert.strictEqual(body.user.username, 'alice');
    aliceToken = body.token;
  });

  await check('login with a wrong password is rejected', async () => {
    const r = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: 'alice', password: 'wrong-password' }),
    });
    assert.strictEqual(r.status, 401);
  });

  await check('login with an unknown user is rejected', async () => {
    const r = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: 'nobody', password: 'whatever123' }),
    });
    assert.strictEqual(r.status, 401);
  });

  await check('SQL injection in the username field does not bypass auth', async () => {
    for (const payload of ["admin' OR '1'='1", "alice'--", "' OR 1=1 --", "alice' OR 'x'='x"]) {
      const r = await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username: payload, password: 'anything' }),
      });
      assert.strictEqual(r.status, 401, `payload was accepted: ${payload}`);
    }
  });

  await check('password is never returned by the API', async () => {
    const r = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: 'bob', password: 'Bob#2026password' }),
    });
    const text = await r.text();
    assert.ok(!/password_hash|passwordHash|\$2[aby]\$/.test(text), 'response looks like it leaks a hash');
    bobToken = JSON.parse(text).token;
  });

  /* ------------------------------------------------------ authorisation */

  await check('GET /api/data without a token returns 401', async () => {
    const r = await api('/api/data');
    assert.strictEqual(r.status, 401);
  });

  await check('GET /api/data with a malformed token returns 401', async () => {
    const r = await api('/api/data', { headers: { authorization: 'Bearer not.a.jwt' } });
    assert.strictEqual(r.status, 401);
  });

  await check('GET /api/data with a valid token returns 200', async () => {
    const r = await api('/api/data', { headers: { authorization: `Bearer ${aliceToken}` } });
    assert.strictEqual(r.status, 200);
    const body = await r.json();
    assert.ok(Array.isArray(body.notes));
  });

  /* --------------------------------------------------------------- XSS */

  await check('XSS payload is neutralised in API responses', async () => {
    const payload = '<script>alert("xss")</script>';
    const r = await api('/api/notes', {
      method: 'POST',
      headers: { authorization: `Bearer ${aliceToken}` },
      body: JSON.stringify({ title: 'xss test', body: payload }),
    });
    assert.strictEqual(r.status, 201);
    const body = await r.json();
    assert.ok(!body.note.body.includes('<script>'), 'raw <script> came back in the response');
    assert.ok(body.note.body.includes('&lt;script&gt;'), 'expected escaped output');
    noteId = body.note.id;

    const read = await api(`/api/notes/${noteId}`, {
      headers: { authorization: `Bearer ${aliceToken}` },
    });
    const readBody = await read.text();
    assert.ok(!readBody.includes('<script>'), 'raw <script> came back when reading the note');
  });

  /* -------------------------------------------------------------- IDOR */

  await check('another user cannot read a note they do not own', async () => {
    const r = await api(`/api/notes/${noteId}`, {
      headers: { authorization: `Bearer ${bobToken}` },
    });
    assert.strictEqual(r.status, 404);
  });

  await check('a note cannot be created without a token', async () => {
    const r = await api('/api/notes', {
      method: 'POST',
      body: JSON.stringify({ title: 't', body: 'b' }),
    });
    assert.strictEqual(r.status, 401);
  });

  /* -------------------------------------------------------- validation */

  await check('empty note title is rejected with 400', async () => {
    const r = await api('/api/notes', {
      method: 'POST',
      headers: { authorization: `Bearer ${aliceToken}` },
      body: JSON.stringify({ title: '   ', body: 'x' }),
    });
    assert.strictEqual(r.status, 400);
  });

  await check('oversized note body is rejected with 400', async () => {
    const r = await api('/api/notes', {
      method: 'POST',
      headers: { authorization: `Bearer ${aliceToken}` },
      body: JSON.stringify({ title: 'ok', body: 'A'.repeat(2001) }),
    });
    assert.strictEqual(r.status, 400);
  });

  await check('unknown route returns 404 JSON, not a stack trace', async () => {
    const r = await api('/does-not-exist');
    assert.strictEqual(r.status, 404);
    const text = await r.text();
    assert.ok(!/at\s+\w+\s+\(/.test(text), 'response contains a stack trace');
  });

  /* ------------------------------------------------------------- report */

  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  server.close();
  process.exit(failed.length === 0 ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  if (server) server.close();
  process.exit(1);
});
