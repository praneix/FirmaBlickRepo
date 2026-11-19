import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
test('dist output includes entry point and its assets',()=>{
  for (const name of ['index.html','site.mjs','styles.css']) assert.ok(existsSync('dist/'+name),name);
  const html=readFileSync('dist/index.html','utf8');
  assert.match(html,/\.\/site\.mjs/);
  assert.match(html,/\.\/styles\.css/);
  assert.match(html,/id="intelligence"/);
});