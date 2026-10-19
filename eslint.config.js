'use strict';
/**
 * ESLint flat configuration -- this is the SAST stage of the pipeline.
 *
 * eslint-plugin-security provides 14 rules that look for Node.js specific
 * dangerous patterns (child_process with user input, eval, non-literal
 * require, unsafe regular expressions, and so on). We also turn on the core
 * rules that matter for an API: no-eval, no-implied-eval and no-new-func.
 */
const js = require('@eslint/js');
const security = require('eslint-plugin-security');

module.exports = [
  {
    ignores: ['node_modules/**', 'data/**', 'reports/**'],
  },
  js.configs.recommended,
  {
    files: ['**/*.js'],
    plugins: { security },
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'commonjs',
      globals: {
        require: 'readonly',
        module: 'writable',
        exports: 'writable',
        __dirname: 'readonly',
        process: 'readonly',
        console: 'readonly',
        Buffer: 'readonly',
        fetch: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
      },
    },
    rules: {
      ...security.configs.recommended.rules,

      // Core rules that catch classic injection and dynamic-code mistakes.
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',

      // Style-level noise that would drown the security signal.
      'no-unused-vars': ['warn', { argsIgnorePattern: '^(_|next|req|res)$' }],
      'no-console': 'off',
    },
  },
];

