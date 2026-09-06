'use strict';
// The only active paper controller. No CDN, polling, sockets or live fallback.
const byId = id => document.getElementById(id);
const pretty = value => JSON.stringify(value, null, 2);
function show(id, value) { if (byId(id)) byId(id).textContent = value; }
async function api(path, method = 'GET', data) {
  const response = await fetch(path, {method, credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, ...(data === undefined ? {} : {body: JSON.stringify(data)})});
  if (response.redirected) throw new Error('Session expired. Log in locally again.');
  const value = await response.json();
  if (!response.ok || value.success === false) throw new Error(value.error || `Request failed (${response.status})`);
  return value;
}
function message(text, error = false) { const node = byId('action-status'); node.textContent = text; node.className = error ? 'error' : 'notice'; }
async function action(fn) {
  const buttons = [...document.querySelectorAll('form button, td button')].filter(node => !node.disabled);
  buttons.forEach(node => node.disabled = true);
  try { await fn(); } catch (error) { message(error.message, true); }
  finally { buttons.forEach(node => node.disabled = false); }
}
function button(label, fn) { const b = document.createElement('button'); b.type = 'button'; b.textContent = label; b.addEventListener('click', () => action(fn)); return b; }
function table(id, rows, fields, controls) {
  const host = byId(id); if (!host) return;
  host.replaceChildren();
  if (!rows.length) { host.textContent = 'No records in this session.'; return; }
  const t = document.createElement('table'), head = t.createTHead().insertRow();
  fields.forEach(([label]) => { const cell = document.createElement('th'); cell.textContent = label; head.append(cell); });
  if (controls) { const cell = document.createElement('th'); cell.textContent = 'Actions'; head.append(cell); }
  const body = t.createTBody();
  rows.forEach(row => {
    const tr = body.insertRow();
    fields.forEach(([, key]) => { const v = row[key]; tr.insertCell().textContent = v == null ? '—' : typeof v === 'object' ? JSON.stringify(v) : String(v); });
    if (controls) controls(tr.insertCell(), row);
  }); host.append(t);
}
async function strategies() {
  if (!byId('strategies') && !byId('backtest-strategy')) return;
  const rows = await api('/api/strategies');
  table('strategies', rows, [['Name','name'],['Pairs','trading_pairs'],['Active','is_active'],['Risk %','risk_per_trade_pct']], (cell, row) => {
    cell.append(button('Edit', async () => editStrategy(row)), button(row.is_active ? 'Deactivate' : 'Activate', async () => {
      await api(`/api/strategies/${row.id}`, 'PUT', {is_active: !row.is_active}); await strategies(); message('Strategy activation saved.');
    }));
  });
  const select = byId('backtest-strategy');
  if (select) { const selected = select.value; select.replaceChildren(); rows.forEach(row => { const option = document.createElement('option'); option.value = row.id; option.textContent = row.name; select.append(option); }); if (rows.some(row => String(row.id) === selected)) select.value = selected; }
}
function editStrategy(row) {
  const config = row.indicators_config;
  const entries = Array.isArray(config) ? config : Object.entries(config).map(([type, parameters]) => ({type, parameters}));
  const rule = row.entry_conditions[0];
  if (entries.length !== 1 || row.trading_pairs.length !== 1 || row.entry_conditions.length !== 1 || row.exit_conditions.length > 1 || !['sma','ema','rsi','macd'].includes(entries[0].type)) throw new Error('This strategy is outside the compact editor schema; edit its JSON through the documented API. No changes were made.');
  const form = byId('strategy-form'), f = form.elements, indicator = entries[0];
  if (indicator.type === 'macd' && ['fast_period','slow_period','signal_period'].some((key,index) => (indicator.parameters?.[key] ?? [12,26,9][index]) !== [12,26,9][index])) throw new Error('Custom MACD periods require the JSON API. No changes were made.');
  if (row.exit_conditions.length && !['>','above'].includes(row.exit_conditions[0].operator)) throw new Error('This exit rule cannot be represented by the compact editor. No changes were made.');
  f.id.value = row.id; f.name.value = row.name; f.pair.value = row.trading_pairs[0]; f.indicator.value = indicator.type;
  f.period.value = indicator.parameters?.period || 1; f.side.value = rule.side || rule.signal_type;
  f.operator.value = ({above: '>', below: '<'}[rule.operator] || rule.operator);
  if (!f.operator.value) throw new Error('Unsupported editor operator. No changes were made.');
  f.threshold.value = rule.value; f.exit_threshold.value = row.exit_conditions[0]?.value ?? '';
  f.risk.value = row.risk_per_trade_pct; f.stop.value = row.stop_loss_pct; f.take.value = row.take_profit_pct; f.active.checked = row.is_active;
  form.scrollIntoView({behavior: 'smooth'}); message(`Editing ${row.name}. Save applies changes to this strategy.`);
}
async function positions() {
  if (!byId('positions')) return;
  const result = await api('/api/positions');
  table('positions', result.data, [['Lot','id'],['Strategy','strategy_id'],['Pair','trading_pair'],['Units','amount'],['Entry USDT','entry_price'],['Mark USDT','current_price']], (cell,row) => cell.append(button('Close paper position', async () => {
    const result = await api(`/api/positions/${row.id}/close`, 'POST', {}); show('manual-result', pretty(result)); await refresh(); message('Owned paper position closed.');
  })));
}
async function signalsAndTrades() {
  if (!byId('signals')) return;
  const signals = await api('/api/signals');
  table('signals', signals, [['Signal','id'],['Strategy','strategy_id'],['UTC time','timestamp'],['Pair','trading_pair'],['Side','signal_type'],['Status','status']], (cell,row) => {
    cell.append(button('Details', async () => { const pre = document.createElement('pre'); pre.textContent = pretty(row); cell.append(pre); }));
    if (row.status === 'pending') {
      const quantity = document.createElement('input'); quantity.type = 'number'; quantity.min = '0.000001'; quantity.step = 'any'; quantity.value = '0.1'; quantity.setAttribute('aria-label', `Quantity for signal ${row.id}`);
      cell.append(quantity, button('Execute paper signal', async () => { await api(`/api/signals/${row.id}/execute`, 'POST', {amount: Number(quantity.value)}); await refresh(); message('Paper signal execution completed.'); }));
    }
  });
  table('trades', await api('/api/trades'), [['Fill','id'],['Strategy','strategy_id'],['UTC time','timestamp'],['Pair','trading_pair'],['Side','order_type'],['Units','amount'],['Price USDT','price'],['Fee USDT','fee'],['Status','status']]);
}
async function histories() {
  if (byId('runs')) table('runs', await api('/api/paper/runs'), [['Run','id'],['Origin','data_origin'],['Start UTC','start_time'],['End UTC','end_time']], (cell,row) => cell.append(button('Show replay result', async () => show('replay-result', pretty(JSON.parse(row.summary))))));
  if (byId('backtests')) table('backtests', await api('/api/backtests'), [['ID','id'],['Strategy','strategy_id'],['Start UTC','start_date'],['End UTC','end_date'],['Final USDT','final_balance'],['Trades','total_trades']], (cell,row) => cell.append(button('Details', async () => show('backtest-result', pretty(await api(`/api/backtests/${row.id}`))))));
}
async function refresh() {
  try {
    const status = await api('/api/paper/status');
    show('clock', status.clock || 'Not started');
    show('data-state', status.state === 'simulated' ? `Simulated historical data · ${status.data_origin} · ${status.timeframe} · fees ${status.fee_bps} bps / slippage ${status.slippage_bps} bps. Quote remains at the replay clock until another replay.` : 'Data unavailable. Create a strategy, then load local candles and run a replay.');
    const balance = (await api('/api/account-balance')).data.paper;
    show('cash', `${balance.cash.toFixed(4)} USDT`); show('equity', `${balance.equity.toFixed(4)} USDT`);
    await strategies(); await positions(); await signalsAndTrades(); await histories();
  } catch (error) { show('data-state', 'Session refresh failed. Displayed values may be stale; no live data connection exists.'); throw error; }
}
function form(id, handler) { const node = byId(id); if (node) node.addEventListener('submit', event => { event.preventDefault(); action(() => handler(Object.fromEntries(new FormData(node)), node)); }); }
form('strategy-form', async (data, node) => {
  const id = 'entry_indicator', indicator = {id, type: data.indicator, parameters: data.indicator === 'macd' ? {fast_period:12,slow_period:26,signal_period:9} : {period:Number(data.period)}};
  const rule = {indicator:`${data.indicator}_${id}`, operator:data.operator, value:Number(data.threshold), side:data.side};
  const payload = {name:data.name,trading_pairs:[data.pair],timeframe:'1h',is_active:node.elements.active.checked,indicators_config:[indicator],entry_conditions:[rule],exit_conditions:data.exit_threshold === '' ? [] : [{indicator:`${data.indicator}_${id}`,operator:'>',value:Number(data.exit_threshold),side:'SELL'}],risk_per_trade_pct:Number(data.risk),stop_loss_pct:Number(data.stop),take_profit_pct:Number(data.take)};
  await api(data.id ? `/api/strategies/${data.id}` : '/api/strategies', data.id ? 'PUT' : 'POST', payload); node.reset(); await strategies(); message('Strategy saved with explicit side and stable indicator reference.');
});
form('replay-form', async data => { const result = await api('/api/paper/replay', 'POST', data); show('replay-result', pretty(result)); await refresh(); message(`Replay complete: ${result.candle_count} candles, ${result.fill_count} fills. Results saved in the configured output folder.`); });
form('manual-form', async data => { const result = await api('/api/execute-trade', 'POST', {...data, amount:Number(data.amount), mode:'paper', platform:'paper'}); show('manual-result', pretty(result)); await refresh(); message(`Paper order ${result.data.status}: ${result.data.amount} units at ${result.data.price} USDT.`); });
form('backtest-form', async data => { const result = await api('/api/backtests', 'POST', {...data,strategy_id:Number(data.strategy_id),initial_balance:Number(data.initial_balance)}); show('backtest-result', pretty(await api(`/api/backtests/${result.backtest_id}`))); await histories(); message('Dated backtest complete using local candles.'); });
form('chart-form', async data => { const result = await api(`/api/chart-data?pair=${encodeURIComponent(data.pair)}&timeframe=1h&limit=100`); table('candles',result.data,[['UTC time','timestamp'],['Open','open'],['High','high'],['Low','low'],['Close','close'],['Volume','volume']]); message(result.data.length ? `Showing ${result.data.length} completed candles from ${result.data_origin}.` : 'Local candle data unavailable for this pair.'); });
byId('refresh').addEventListener('click', () => action(refresh));
action(refresh);
