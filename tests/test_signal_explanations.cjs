// Exercise the actual controller with synthetic API data and an in-memory DOM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../trading_stack/static/js/paper.js'), 'utf8');
const tables = {}, calls = [];
const sandbox = {document: {getElementById: () => null}, console};
vm.createContext(sandbox);
// Skip page startup/event wiring; invoke the real rendering function explicitly.
vm.runInContext(source.slice(0, source.indexOf("form('strategy-form'")), sandbox);
sandbox.rows = [
  {id: 10, status: 'rejected'}, {id: 11, status: 'pending'},
  {id: 12, status: 'rejected'}, {id: 13, status: 'executed'}, {id: 14, status: 'rejected'}
];
sandbox.decisions = [
  {id: 3, signal_id: 10, status: 'rejected', reason: 'shared_pair_exposure'},
  {id: 2, signal_id: 999, status: 'rejected', reason: 'UNRELATED'},
  {id: 1, signal_id: 10, status: 'rejected', reason: 'risk_per_trade_limit'},
  {id: 4, signal_id: 13, status: 'filled', reason: 'signal_entry'},
  {id: 5, signal_id: null, status: 'filled', reason: 'UNRELATED'},
  {id: 6, signal_id: 14, status: 'rejected', reason: 'future_guard'}
];
sandbox.capture = (id, rows, fields, controls) => { tables[id] = {rows, fields, controls}; };
sandbox.request = async (route, method = 'GET', body) => {
  assert.equal(method, 'GET');
  assert.equal(body, undefined);
  calls.push(route);
  if (route === '/api/signals') return sandbox.rows;
  if (route === '/api/paper/decisions') return sandbox.decisions;
  if (route === '/api/trades') return [];
  throw new Error('Unexpected request');
};
sandbox.document.getElementById = () => ({});
sandbox.document.createElement = () => ({textContent: ''});
vm.runInContext('table = capture; api = request; button = (label, fn) => ({label, fn});', sandbox);
(async () => {
  await vm.runInContext('signalsAndTrades()', sandbox);
  const result = tables.signals;
  assert.ok(result.fields.some(([label]) => label === 'Reason'), 'Signals need a visible reason column');
  assert.match(result.rows[0].decision_explanation, /already held/i);
  assert.match(result.rows[0].decision_explanation, /shared_pair_exposure/);
  assert.equal(result.rows[0].decision_history.length, 2);
  assert.equal(result.rows[1].decision_history.length, 0);
  assert.match(result.rows[1].decision_explanation, /awaiting/i);
  assert.match(result.rows[2].decision_explanation, /no linked decision/i);
  assert.match(result.rows[3].decision_explanation, /filled/i);
  assert.match(result.rows[4].decision_explanation, /future_guard/);
  const children = [];
  result.controls({append: (...nodes) => children.push(...nodes)}, result.rows[0]);
  await children[0].fn();
  assert.match(children[1].textContent, /shared_pair_exposure/);
  assert.doesNotMatch(children[1].textContent, /UNRELATED/);
  assert.equal(children.length, 2, 'Rejected signal cannot acquire an execute action');
  assert.deepEqual(calls.sort(), ['/api/paper/decisions', '/api/signals', '/api/trades'].sort());
  sandbox.request = async () => { throw new Error('synthetic decision retrieval failed'); };
  vm.runInContext('api = request', sandbox);
  await assert.rejects(vm.runInContext('signalsAndTrades()', sandbox), /retrieval failed/);
  console.log('Signal explanations: visible cause, linked details, missing evidence and read-only requests verified.');
})().catch(error => { console.error(error); process.exitCode = 1; });
