// Exercise preference persistence without requiring a browser or a DOM package.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../site/theme.js'), 'utf8');
function boot(saved, blocked = false) {
  const callbacks = {};
  const controls = [0, 1].map(() => ({ value: '', addEventListener(type, fn) { this[type] = fn; } }));
  const document = { documentElement: { dataset: {} }, addEventListener(type, fn) { callbacks[type] = fn; }, querySelectorAll() { return controls; } };
  const localStorage = { getItem() { if (blocked) throw Error(); return saved; }, setItem(key, value) { if (blocked) throw Error(); saved = value; } };
  vm.runInNewContext(source, { document, localStorage });
  callbacks.DOMContentLoaded();
  return { document, controls, saved: () => saved };
}
for (const mode of ['system', 'light', 'dark']) {
  const env = boot(mode);
  assert.equal(env.document.documentElement.dataset.theme, mode);
  env.controls[0].value = 'dark'; env.controls[0].change();
  assert.equal(env.controls[1].value, 'dark'); assert.equal(env.saved(), 'dark');
  env.controls[1].value = 'system'; env.controls[1].change();
  assert.equal(env.document.documentElement.dataset.theme, 'system');
}
assert.equal(boot('invalid').document.documentElement.dataset.theme, 'system');
const blocked = boot(null, true);
blocked.controls[0].value = 'dark'; blocked.controls[0].change();
assert.equal(blocked.document.documentElement.dataset.theme, 'dark');
console.log('Theme preference, synchronized controls, system mode and storage failure checks passed.');
