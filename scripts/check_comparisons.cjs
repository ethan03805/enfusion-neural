const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../site/compare.js'), 'utf8');

function fixture({ loaded = true, mismatch = false, dataset = {} } = {}) {
  const images = [0, 1].map(i => ({ complete: loaded, naturalWidth: loaded ? 1839 + (mismatch ? i : 0) : 0,
    naturalHeight: 947, addEventListener(name, fn) { this[name] = fn; } }));
  const output = {};
  const range = { value: '50', attributes: {}, addEventListener(name, fn) { this[name] = fn; },
    setAttribute(name, value) { this.attributes[name] = value; } };
  const control = { hidden: true, querySelector: selector => selector === 'input' ? range : output };
  const properties = {}, classes = new Set();
  const element = { dataset, querySelectorAll: () => images, querySelector: () => control,
    style: { setProperty: (name, value) => properties[name] = value }, classList: { add: name => classes.add(name) } };
  vm.runInNewContext(source, { document: { querySelectorAll: () => [element] } });
  return { images, output, range, control, properties, classes };
}

const pair = fixture();
assert.equal(pair.control.hidden, false);
assert.equal(pair.properties['--reveal'], '50%');
for (const value of [0, 25, 100]) {
  pair.range.value = String(value); pair.range.input();
  assert.equal(pair.properties['--reveal'], `${value}%`);
  assert.equal(pair.range.attributes['aria-valuetext'], `${value}% original, ${100 - value}% model output`);
  assert.equal(pair.output.textContent, `${value}% original`);
}
const pending = fixture({ loaded: false });
assert.equal(pending.control.hidden, true);
pending.images[0].complete = true; pending.images[0].naturalWidth = 1839; pending.images[0].load();
assert.equal(pending.control.hidden, true);
pending.images[1].complete = true; pending.images[1].naturalWidth = 1839; pending.images[1].load();
assert.equal(pending.control.hidden, false);
const mismatch = fixture({ mismatch: true });
assert.equal(mismatch.control.hidden, true);
assert.equal(mismatch.classes.size, 0);
const sources = fixture({ dataset: { beforeLabel: '6-update source', afterLabel: '120-update source' } });
assert.equal(sources.range.attributes['aria-valuetext'], '50% 6-update source, 50% 120-update source');
assert.equal(sources.output.textContent, '50% 6-update source');
console.log('Comparison controls: endpoints, accessible labels, delayed images and size mismatch passed.');
