'use strict';
/**
 * Smoke demonstration of the API, used when the container has no curl.
 *
 * Runs four requests against a locally listening server and prints a transcript:
 *   1. GET  /api/data          without a token   -> 401 (access is restricted)
 *   2. POST /auth/login        valid credentials -> token issued
 *   3. GET  /api/data          with the token    -> the caller's notes
 *   4. GET  /api/notes/1       as another user   -> 404 (no IDOR)
 *
 * Usage:  node scripts/demo.js [baseUrl]
 * Default base URL: http://127.0.0.1:3000
 */
const http = require('http');
const { URL } = require('node:url');

const BASE = process.argv[2] || 'http://127.0.0.1:3000';
const url = new URL(BASE);

function request({ method = 'GET', path, body, token }) {
  return new Promise((resolve, reject) => {
    const payload = body ? Buffer.from(JSON.stringify(body)) : null;
    const headers = {};
    if (payload) {
      headers['Content-Type'] = 'application/json';
      headers['Content-Length'] = payload.length;
    }
    if (token) headers.Authorization = `Bearer ${token}`;

    const req = http.request(
      { host: url.hostname, port: url.port, path, method, headers },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          let parsed = null;
          try {
            parsed = JSON.parse(data);
          } catch {
            parsed = data;
          }
          resolve({ status: res.statusCode, body: parsed });
        });
      },
    );
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

const line = (label, r) =>
  console.log(`${label.padEnd(46)} -> HTTP ${r.status}  ${JSON.stringify(r.body)}`);

(async () => {
  console.log(`\nSecure Notes API - smoke demonstration (${BASE})\n`);

  const anon = await request({ path: '/api/data' });
  line('1. GET /api/data (no token)', anon);

  const login = await request({
    method: 'POST',
    path: '/auth/login',
    body: { username: 'alice', password: 'Alice#2026pass' },
  });
  const token = login.body?.token;
  line('2. POST /auth/login (alice)', {
    status: login.status,
    body: { token: token ? `${token.slice(0, 24)}...` : null, user: login.body?.user },
  });

  const own = await request({ path: '/api/data', token });
  line('3. GET /api/data (alice, with token)', own);

  // bob owns note id 2 in a freshly seeded database; alice must not read it.
  const bobLogin = await request({
    method: 'POST',
    path: '/auth/login',
    body: { username: 'bob', password: 'Bob#2026password' },
  });
  const created = await request({
    method: 'POST',
    path: '/api/notes',
    token: bobLogin.body?.token,
    body: { title: "bob's private note", body: 'alice must not be able to read this' },
  });
  const bobNoteId = created.body?.note?.id;
  const idor = await request({ path: `/api/notes/${bobNoteId}`, token });
  line(`4. GET /api/notes/${bobNoteId} (alice reading bob's note)`, idor);

  console.log('\nExpected: 401, token issued, alice sees only her notes, 404 on the last one.\n');
})().catch((err) => {
  console.error('request failed:', err.message);
  process.exit(1);
});
