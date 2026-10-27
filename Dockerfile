# Secure Notes API — container image
#
# Pure-JavaScript dependencies only (bcryptjs, not bcrypt), and SQLite comes from
# the built-in node:sqlite module, so the image needs no build toolchain and
# alpine is safe.
#
# Run it:
#   docker build -t secure-notes-api .
#   docker run --rm -p 3000:3000 secure-notes-api

FROM node:24-alpine

WORKDIR /app

# Dependencies first, so this layer is cached while only source files change.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Only what the server needs at runtime: no tests, no evidence, no report.
COPY src ./src
COPY scripts ./scripts

RUN mkdir -p data && chown -R node:node /app

# Run unprivileged — the node image already provides this user.
USER node

ENV PORT=3000 \
    DB_PATH=/app/data/app.db \
    NODE_ENV=production

EXPOSE 3000

# JWT_SECRET is mandatory in production, so a random one is generated per start
# unless the operator supplies it. Sessions therefore do not survive a restart,
# which is the correct behaviour for a container that can be replaced at any time.
# The seed script is idempotent: existing accounts are skipped, not duplicated.
CMD ["sh", "-c", "export JWT_SECRET=\"${JWT_SECRET:-$(head -c 32 /dev/urandom | base64)}\" && npm run seed && exec node src/app.js"]
