/* Runs only the real smoke script's cleanup against in-memory fakes. No browser,
   process, socket or filesystem mutation is performed by the tested cleanup. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {EventEmitter} = require('node:events');
const source = fs.readFileSync(require('node:path').join(__dirname,'browser_paper_smoke.cjs'),'utf8');
const trailer = source.slice(source.indexOf('main().catch')).replace('main()', 'Promise.resolve()');
async function check(closeFails, exits) {
  const server = new EventEmitter(); server.exitCode = null; server.kills = 0;
  server.kill = () => {server.kills++; if (exits) {server.exitCode=0; queueMicrotask(() => server.emit('exit',0));} return true;};
  const writes = [];
  const results = {success:true};
  const sandbox = {Promise, context:{close:async () => {if(closeFails) throw new Error('synthetic close failure');}}, server, results,
    output:'synthetic',artifacts:'memory-only',origin:undefined,process:{exitCode:0},console:{log(){},error(){}},
    setTimeout:(fn,ms) => setTimeout(fn,Math.min(ms,15)),clearTimeout,
    fs:{writeFileSync:(name,content) => writes.push({name,content})},path:require('node:path')};
  let error;
  try {await vm.runInNewContext(trailer,sandbox);} catch(caught) {error=caught;}
  assert.equal(server.kills,1,'owned server termination must be attempted despite context.close failure');
  assert.equal(writes.length,2,'launcher and result evidence must survive cleanup failures');
  if(closeFails) assert.ok(JSON.stringify(results).includes('synthetic close failure'));
  if(!exits) assert.ok(JSON.stringify(results).includes('timeout'));
  assert.equal(error,undefined,'cleanup should record errors without losing evidence');
}
(async () => {await check(true,true); await check(false,false); await check(false,true); console.log('Browser cleanup PASS: close failure, bounded termination timeout, normal exit; fake processes only.');})().catch(error => {console.error(error);process.exitCode=1;});
