'use strict';
/**
 * Input validation and output encoding helpers.
 *
 * Two different problems are handled here and it is important not to mix
 * them up:
 *
 *   validation  -- decide whether an input is acceptable at all (length,
 *                  character class, type). Reject early with 400.
 *   encoding    -- when data goes back to a client, make sure that any
 *                  character with meaning in HTML is neutralised, so that a
 *                  stored payload can never execute in a browser.
 */
const escapeHtml = require('escape-html');

const USERNAME_RE = /^[A-Za-z0-9_.-]{3,32}$/;

class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ValidationError';
    this.status = 400;
  }
}

/** Coerce to string, trim, enforce a maximum length. */
function requireString(value, field, { min = 1, max = 255 } = {}) {
  if (typeof value !== 'string') {
    throw new ValidationError(`${field} must be a string`);
  }
  const v = value.trim();
  if (v.length < min) {
    throw new ValidationError(`${field} must be at least ${min} character(s)`);
  }
  if (v.length > max) {
    throw new ValidationError(`${field} must be at most ${max} characters`);
  }
  return v;
}

function requireUsername(value) {
  const v = requireString(value, 'username', { min: 3, max: 32 });
  if (!USERNAME_RE.test(v)) {
    throw new ValidationError('username may only contain letters, digits, dot, dash and underscore');
  }
  return v;
}

function requirePassword(value) {
  // Passwords are NOT escaped and NOT trimmed: any character is legitimate,
  // and whitespace may be significant. Only the length is constrained.
  if (typeof value !== 'string') {
    throw new ValidationError('password must be a string');
  }
  if (value.length < 8) {
    throw new ValidationError('password must be at least 8 characters');
  }
  if (value.length > 128) {
    throw new ValidationError('password must be at most 128 characters');
  }
  return value;
}

/**
 * Escape every user-controlled string on the way out.
 *
 * The API speaks JSON, so escaping is not strictly required for correctness,
 * but the manual asks for all user data in responses to be sanitised, and it
 * is genuine defence in depth: the most common client bug is to take a value
 * from this JSON and drop it into innerHTML. If the value already arrives as
 * &lt;script&gt;, that mistake stops being an XSS.
 */
function encodeForOutput(value) {
  if (typeof value === 'string') return escapeHtml(value);
  if (Array.isArray(value)) return value.map(encodeForOutput);
  if (value && typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) out[k] = encodeForOutput(v);
    return out;
  }
  return value;
}

module.exports = {
  ValidationError,
  requireString,
  requireUsername,
  requirePassword,
  encodeForOutput,
  escapeHtml,
};

