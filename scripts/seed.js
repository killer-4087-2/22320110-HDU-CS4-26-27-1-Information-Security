'use strict';
/** Create the demo accounts. Run with: npm run seed */
const bcrypt = require('bcryptjs');
const { openDb, q } = require('../src/db');

const ACCOUNTS = [
  { username: 'alice', password: 'Alice#2026pass', role: 'user' },
  { username: 'bob', password: 'Bob#2026password', role: 'user' },
  { username: 'admin', password: 'Admin#2026pass', role: 'admin' },
];

function seed() {
  const db = openDb();
  for (const a of ACCOUNTS) {
    if (q.findUserByUsername(db, a.username)) {
      console.log(`exists   ${a.username}`);
      continue;
    }
    const hash = bcrypt.hashSync(a.password, 10);
    q.createUser(db, a.username, hash, a.role);
    console.log(`created  ${a.username} (${a.role})`);
  }
  // one sample note for alice
  const alice = q.findUserByUsername(db, 'alice');
  if (alice && q.listNotesByOwner(db, alice.id).length === 0) {
    q.createNote(db, alice.id, 'Welcome', 'This note was created by the seed script.');
    console.log('created  sample note for alice');
  }
  console.log(`total users: ${q.countUsers(db)}`);
}

seed();
