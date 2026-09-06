/* Finite authorized browser verification. Keeps profile and all artifacts.
   Run only after the guarded offline suite passes; this file is not discovered by it. */
const fs = require('node:fs');
const path = require('node:path');
const {spawn} = require('node:child_process');
const {randomUUID} = require('node:crypto');
const assert = require('node:assert/strict');
const {chromium} = require('C:/Users/Blair/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const artifacts = path.join(root, 'paper_trading/state/test-artifacts', `browser-${randomUUID()}`);
const profile = path.join(artifacts, 'profile'), browserArtifacts = path.join(artifacts, 'browser-artifacts');
for (const dir of [artifacts, profile, browserArtifacts]) fs.mkdirSync(dir, {recursive:true});
console.log(`Preserved browser evidence: ${artifacts}`);
let context, server, output = '', origin;
const results = {mode:'paper', data_origin:'synthetic_ui_fixture', actions:[], errors:[], blocked:[]};
const step = text => { results.actions.push(text); console.log(text); };
async function editorRegression(page) {
  const baseline = await page.evaluate(async () => (await (await fetch('/api/strategies')).json())[0]);
  const failures = [];
  const snapshot = () => page.locator('#strategy-form').evaluate(form => [...form.elements].filter(field => field.name).map(field => ({name:field.name,value:field.value,checked:field.checked})));
  const saveFixture = async changes => page.evaluate(async ({base,changes}) => {
    const data = {...base, ...changes, is_active:false}; delete data.id;
    const response = await fetch('/api/strategies',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result = await response.json(); if (!response.ok) throw new Error(result.error);
    return (await fetch(`/api/strategies/${result.strategy_id}`)).json();
  }, {base:baseline,changes});
  const cases = [
    ['entry price', {entry_conditions:[{indicator:'price',operator:'>',value:2,side:'BUY'}]}],
    ['entry close', {entry_conditions:[{indicator:'close',operator:'>',value:2,side:'BUY'}]}],
    ['equals', {entry_conditions:[{indicator:'sma',operator:'equals',value:2,side:'BUY'}]}],
    ['above or equal', {entry_conditions:[{indicator:'sma',operator:'>=',value:2,side:'BUY'}]}],
    ['exit price', {exit_conditions:[{indicator:'price',operator:'>',value:2,side:'SELL'}]}],
    ['exit BUY', {exit_conditions:[{indicator:'sma',operator:'>',value:2,side:'BUY'}]}],
    ['custom MACD', {indicators_config:{macd:{fast_period:5}},entry_conditions:[{indicator:'macd',operator:'>',value:2,side:'BUY'}],exit_conditions:[]}],
  ];
  for (const [name, changes] of cases) {
    const row = await saveFixture({name:`Editor rejection ${name}`,...changes});
    await page.getByRole('button',{name:'Refresh session',exact:true}).click();
    await page.waitForFunction(name => [...document.querySelectorAll('#strategies tbody tr')].some(row => row.textContent.includes(name)),row.name);
    // Retain a deliberately non-default unsaved form to expose partial writes.
    await page.locator('#strategy-form [name=name]').fill('Unsaved local draft');
    await page.locator('#strategy-form [name=threshold]').fill('777');
    const before = await snapshot();
    await page.locator('#strategies tbody tr').filter({hasText:row.name}).getByRole('button',{name:'Edit',exact:true}).click();
    await page.waitForTimeout(50);
    try { assert.match(await page.locator('#action-status').innerText(),/No changes were made/); assert.deepEqual(await snapshot(),before); }
    catch (error) { failures.push(`${name}: ${error.message}`); }
  }
  // The launcher uses 1h. Feed the real DOM editor an otherwise accepted row
  // carrying 4h to verify it refuses instead of silently forcing the save to 1h.
  const beforeTimeframe = await snapshot();
  const timeframeError = await page.evaluate(row => {try {editStrategy({...row,timeframe:'4h'});return null;} catch(error) {return error.message;}},baseline);
  try { assert.match(timeframeError || '',/No changes were made/); assert.deepEqual(await snapshot(),beforeTimeframe); }
  catch(error) { failures.push(`non-1h timeframe: ${error.message}`); }
  for (const [type,period] of [['sma',20],['ema',20],['rsi',14]]) {
    const row = await saveFixture({name:`Default ${type}`,indicators_config:{[type]:{}},entry_conditions:[{indicator:type,operator:'>',value:1,side:'BUY'}],exit_conditions:[]});
    await page.getByRole('button',{name:'Refresh session',exact:true}).click();
    await page.waitForFunction(name => [...document.querySelectorAll('#strategies tbody tr')].some(row => row.textContent.includes(name)),row.name);
    await page.locator('#strategies tbody tr').filter({hasText:row.name}).getByRole('button',{name:'Edit',exact:true}).click();
    try { assert.equal(await page.locator('#strategy-form [name=period]').inputValue(),String(period)); }
    catch(error) { failures.push(`default ${type}: ${error.message}`); continue; }
    await page.locator('#strategy-form [name=name]').fill(`${row.name} renamed`);
    await page.getByRole('button',{name:'Save strategy',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('#action-status').textContent.includes('Strategy saved'));
    const saved = await page.evaluate(async id => (await fetch(`/api/strategies/${id}`)).json(),row.id);
    try { assert.equal(saved.indicators_config[0].parameters.period,period); assert.equal(saved.entry_conditions[0].side,'BUY'); assert.equal(saved.timeframe,'1h'); assert.deepEqual(saved.exit_conditions,[]); }
    catch(error) { failures.push(`round-trip ${type}: ${error.message}`); }
  }
  results.editorRegressions = {rejectedCases:cases.length + 1,defaultRoundTrips:3,failures};
  await page.screenshot({path:path.join(artifacts,'05-editor-regressions.png'),fullPage:true});
  assert.deepEqual(failures,[]);
  step('Editor regression PASS: eight refused shapes leave every form field unchanged; three default-period name edits preserve semantics.');
}
async function main() {
  server = spawn(path.join(root, '.venv-paper/Scripts/python.exe'), ['-B','-m','trading_stack.paper_server','--data-root',path.join(root,'tests/fixtures/paper-session'),'--output-root',artifacts,'--port','0'], {cwd:root, windowsHide:true, env:{...process.env, PYTHONDONTWRITEBYTECODE:'1',TEAKA_MODE:'paper'}});
  server.stdout.on('data', data => { output += data.toString(); });
  server.stderr.on('data', data => { output += data.toString(); });
  origin = await new Promise((resolve,reject) => {
    const timer = setTimeout(() => reject(new Error('Launcher timeout')),20000);
    server.stdout.on('data', () => { const match = output.match(/PAPER_URL=(http:\/\/127\.0\.0\.1:\d+)/); if (match) {clearTimeout(timer);resolve(match[1]);} });
    server.on('exit', code => {clearTimeout(timer);reject(new Error(`Launcher exited ${code}`));});
  });
  results.origin = origin;
  context = await chromium.launchPersistentContext(profile, {executablePath:'C:/Users/Blair/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe',artifactsDir:browserArtifacts,headless:true,viewport:{width:1440,height:1080},acceptDownloads:false,serviceWorkers:'block'});
  await context.route('**/*', route => {
    if (new URL(route.request().url()).origin === origin) return route.continue();
    results.blocked.push(route.request().url()); return route.abort();
  });
  await context.routeWebSocket('**/*', socket => socket.close());
  const page = context.pages()[0]; page.on('pageerror', error => results.errors.push(error.message));
  await page.goto(`${origin}/auth/register`);
  const password = randomUUID();
  await page.locator('[name=username]').fill('paper_browser_fixture');
  await page.locator('[name=email]').fill('paper-browser@example.invalid');
  await page.locator('[name=password]').fill(password); await page.locator('[name=confirm_password]').fill(password);
  await page.getByRole('button',{name:'Create session user',exact:true}).click();
  await page.locator('[name=username]').fill('paper_browser_fixture'); await page.locator('[name=password]').fill(password);
  await page.getByRole('button',{name:'Log in locally',exact:true}).click();
  await page.waitForURL('**/dashboard');
  await page.waitForFunction(() => document.querySelector('#cash').textContent.includes('USDT'));
  step('Registered and logged in disposable memory-only user through local forms.');
  await page.locator('#strategy-form [name=exit_threshold]').fill('102');
  await page.getByRole('button',{name:'Save strategy',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#action-status').textContent.includes('Strategy saved'));
  let definitions = await page.evaluate(async () => (await fetch('/api/strategies')).json());
  assert.equal(definitions[0].entry_conditions[0].side,'BUY'); assert.equal(definitions[0].exit_conditions[0].side,'SELL');
  await page.locator('#strategy-form [name=name]').fill('Synthetic SELL-only example');
  await page.locator('#strategy-form [name=side]').selectOption('SELL');
  await page.getByRole('button',{name:'Save strategy',exact:true}).click();
  await page.waitForFunction(() => document.querySelectorAll('#strategies tbody tr').length === 2);
  step('Created BUY strategy with explicit SELL exit and second SELL-only strategy using rendered editor.');
  if (process.argv.includes('--editor-only')) { await editorRegression(page); results.success = true; return; }
  await page.locator('summary').click();
  await page.screenshot({path:path.join(artifacts,'01-ready-to-replay.png'),fullPage:true});
  await page.getByRole('button',{name:'Run finite replay',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#action-status').textContent.includes('Replay complete'));
  const replay = JSON.parse(await page.locator('#replay-result').innerText());
  assert.ok(replay.fill_count >= 2); assert.equal(replay.candle_count,5); assert.ok(replay.source_sha256);
  assert.equal(replay.decisions.length,replay.decision_count);
  assert.ok(replay.decisions.some(row => row.signal_id && row.execution_id));
  assert.ok(replay.decisions.some(row => row.status === 'rejected' && row.reason === 'no_owned_position'));
  results.decisionAudit = {rendered:replay.decisions.length,linked:replay.decisions.filter(row => row.execution_id).length};
  results.replay = replay; results.cashAfterReplay = await page.locator('#cash').innerText();
  step('Replayed five synthetic candles through local CSV/range/origin form; inspected actual fills, cash, source hash.');
  await page.getByRole('button',{name:'Submit paper order',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#action-status').textContent.includes('Paper order filled'));
  assert.equal(JSON.parse(await page.locator('#manual-result').innerText()).data.status,'filled');
  await page.getByRole('button',{name:'Close paper position',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#action-status').textContent.includes('position closed'));
  assert.ok((await page.locator('#positions').innerText()).includes('No records'));
  results.manualClose = JSON.parse(await page.locator('#manual-result').innerText());
  step('Submitted 0.1-unit paper BUY and closed the owned position through rendered controls.');
  await page.screenshot({path:path.join(artifacts,'02-replay-and-manual-close.png'),fullPage:true});
  await page.getByRole('link',{name:'Candles',exact:true}).click();
  await page.getByRole('button',{name:'Show candles',exact:true}).click();
  await page.waitForFunction(() => document.querySelectorAll('#candles tbody tr').length === 5);
  step('Inspected five completed candles on local market-data page.');
  await page.getByRole('link',{name:'Signals & fills',exact:true}).click();
  await page.waitForFunction(() => document.querySelectorAll('#trades tbody tr').length >= 4);
  step('Verified real signal and execution tables on the signals page.');
  await page.getByRole('link',{name:'Backtesting',exact:true}).click();
  await page.waitForFunction(() => document.querySelectorAll('#backtest-strategy option').length === 2);
  await page.getByRole('button',{name:'Run dated backtest',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#action-status').textContent.includes('Dated backtest complete'));
  results.backtest = JSON.parse(await page.locator('#backtest-result').innerText());
  assert.equal(results.backtest.trading_pair,'BTC/USDT'); assert.ok(results.backtest.total_trades > 0);
  await page.screenshot({path:path.join(artifacts,'03-dated-backtest.png'),fullPage:true});
  step('Executed dated owned-strategy backtest with actual local results and history.');
  await page.getByRole('link',{name:'Settings',exact:true}).click();
  await page.locator('[name=max_position_size_pct]').fill('6');
  await page.getByRole('button',{name:'Save paper risk settings',exact:true}).click();
  assert.ok((await page.locator('body').innerText()).includes('Paper risk settings saved'));
  await page.screenshot({path:path.join(artifacts,'04-settings.png'),fullPage:true});
  await page.getByRole('link',{name:'Profile',exact:true}).click();
  assert.ok((await page.locator('body').innerText()).includes('Profile and password changes are unavailable'));
  step('Saved paper risk settings; verified truthful disabled account/notification/profile controls.');
  // A blocked own-origin API request must visibly mark any retained values stale.
  await page.getByRole('link',{name:'Session',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#cash').textContent.includes('USDT'));
  await editorRegression(page);
  await page.route('**/api/paper/status', route => route.abort());
  await page.getByRole('button',{name:'Refresh session',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#data-state').textContent.includes('may be stale'));
  step('Forced API refresh failure and verified visible stale/unavailable warning.');
  assert.deepEqual(results.errors,[]);
  results.success = true;
}
main().catch(error => { results.failure = error.stack; process.exitCode = 1; console.error(error.message); }).finally(async () => {
  results.cleanupErrors = [];
  const record = error => {results.cleanupErrors.push(error.message);results.success=false;process.exitCode=1;};
  const bounded = async (work, label, timeout=10000) => {
    let timer;
    try {await Promise.race([work,new Promise((_,reject) => {timer=setTimeout(() => reject(new Error(`${label} timeout`)),timeout);})]);}
    finally {clearTimeout(timer);}
  };
  try {
    if (context) await bounded(context.close(),'Browser close',45000);
    results.browserClosed = true;
  } catch(error) {record(error);}
  try {
    if (server && server.exitCode === null) {
      const exited = new Promise(resolve => server.once('exit',resolve));
      server.kill();
      await bounded(exited,'Owned server termination');
    }
    results.ownedServerStopped = !server || server.exitCode !== null || server.signalCode != null;
  } catch(error) {record(error);results.ownedServerStopped=false;}
  finally {
    try {fs.writeFileSync(path.join(artifacts,'launcher-output.txt'),output);} catch(error) {record(error);}
    fs.writeFileSync(path.join(artifacts,'browser-results.json'),JSON.stringify(results,null,2));
  }
  console.log(results.success && results.ownedServerStopped ? 'Browser smoke PASS; owned processes stopped; artifacts retained.' : 'Browser smoke FAILED; inspect preserved cleanup evidence.');
});
