#!/usr/bin/env node
'use strict';
// Store submission metadata is checked separately from the SDK/package validator.
// Policy: Otzaria/Otzaria_Website src/app/api/plugins/upload/route.js,
// src/lib/pluginSubmission.js and src/lib/pluginStatus.js.
const fs = require('node:fs');
const path = require('node:path');
const file = process.argv[2] || path.join(__dirname, '../plugin/manifest.json');
const manifest = JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const errors = [];
for (const field of ['id', 'name', 'author', 'description', 'version', 'entrypoint', 'minAppVersion', 'sdkVersion']) {
  if (typeof manifest[field] !== 'string' || !manifest[field].trim()) errors.push(`Missing required field: ${field}`);
}
for (const [field, limit] of Object.entries({name:14, author:100, description:150, version:30, homepage:500})) {
  if (typeof manifest[field] === 'string' && manifest[field].trim().length > limit) errors.push(`${field} exceeds ${limit} characters`);
}
const versionRE = /^\d+\.\d+\.\d+(?:\+.*)?$/;
if (!versionRE.test(manifest.version || '')) errors.push('version must use X.Y.Z format (optional +build metadata)');
const min = manifest.minAppVersion || '';
if (!versionRE.test(min)) errors.push('minAppVersion must use X.Y.Z format');
else {
  const parts = min.split('+')[0].split('.').map(Number);
  const floor = [0, 9, 89];
  const difference = parts.map((n, i) => n - floor[i]).find(n => n !== 0) || 0;
  if (difference < 0) errors.push('The store requires minAppVersion >= 0.9.89');
}
const title = manifest.contributes?.toolTab?.title;
if (title !== undefined && title !== manifest.name) errors.push('toolTab.title must match name');
if (manifest.stability !== undefined && !['stable', 'beta', 'experimental'].includes(manifest.stability)) errors.push('Invalid stability value');
if (manifest.homepage) {
  try { if (!['http:', 'https:'].includes(new URL(manifest.homepage).protocol)) throw Error(); }
  catch { errors.push('homepage must be a valid HTTP(S) URL'); }
}
if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
else console.log(`Store manifest metadata passed: ${manifest.name} ${manifest.version}; author ${manifest.author}`);
