# Fix for CVE-2017-14849

## Summary

| | |
|---|---|
| CVE | CVE-2017-14849 |
| Component | Node.js 8.5.0 (`lib/path.js`, `path.normalize`) |
| Class | CWE-22 Path Traversal / CWE-706 Use of Incorrectly-Resolved Name |
| CVSS v3 | 7.5 (High) |
| Fixed in | Node.js 8.6.0 (and every later release) |

## Files in this folder

| File | Purpose |
|---|---|
| `Dockerfile.node-8.6.0` | **Minimal fix** — bump the base image from `vulhub/node:8.5.0` to `node:8.6.0`. The first version that does not contain the defect. |
| `Dockerfile.node-20` | **Recommended fix** — move to a supported LTS runtime, run as a non-root user, install with `npm ci --omit=dev`. |
| `docker-compose.fixed.yml` | Compose file pointing at the fixed Dockerfile. |

## Why this is the right fix

The vulnerable code is **not** in the application. `www/app.js` is an ordinary
Express static file server and is byte-for-byte identical before and after the
fix. The defect lives in the language runtime:

```
Node.js 8.5.0   path.normalize('../foo/../../secret.txt')  ->  'secret.txt'
Node.js 24      path.normalize('../foo/../../secret.txt')  ->  '..\..\secret.txt'
```

`sender`/`send@0.15.6` defends itself by normalising the requested path and
then rejecting it if any `..` segment survives:

```js
if (UP_PATH_REGEXP.test(normalize('.' + sep + path))) return this.error(403)
```

Because `normalize` wrongly *removed* the `..` segments in 8.5.0, that guard
saw a clean path and let the request through. Downgrading, rewriting the
application, or adding an input filter upstream would all be workarounds
around a broken standard-library function. Replacing the runtime is the only
fix that restores the invariant the guard depends on.

## Applying the fix

```bash
# minimal
docker compose -f fixes/docker-compose.fixed.yml down
docker compose -f fixes/docker-compose.fixed.yml up --build -d

# recommended: edit the base image in the Dockerfile instead
sed -i 's/FROM vulhub\/node:8.5.0/FROM node:20-alpine/' Dockerfile
docker compose down && docker compose up --build -d
```

## Verification performed

Same request, same application, two runtimes:

```
GET /static/../foo/../../secret.txt

Node 8.5.0  ->  HTTP/1.1 200 OK
                SECRET_FLAG{this-file-lives-outside-the-static-root}

Node 24     ->  HTTP/1.1 404 Not Found
```

Regression check on the fixed runtime: `GET /static/main.js` returns 200 and
`GET /` returns 200, so the static server still does its job.
