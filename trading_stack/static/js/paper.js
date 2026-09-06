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
  const refuse = () => { throw new Error('This strategy cannot be represented by the compact editor; use the JSON API. No changes were made.'); };
  const form = byId('strategy-form'), f = form.elements;
  const config = row.indicators_config;
  if (!config || typeof config !== 'object') return refuse();
  const entries = Array.isArray(config) ? config : Object.entries(config).map(([type, parameters]) => ({id:type,type,parameters}));
  if (row.timeframe !== '1h' || row.use_ml_model || entries.length !== 1 || row.trading_pairs.length !== 1 || row.entry_conditions.length !== 1 || row.exit_conditions.length > 1) return refuse();
  const indicator = entries[0], type = indicator.type, params = indicator.parameters || {};
  const defaults = {sma:20,ema:20,rsi:14};
  if (!['sma','ema','rsi','macd'].includes(type)) return refuse();
  const period = params.period ?? defaults[type] ?? 1;
  const allowedParams = type === 'macd' ? ['fast_period','slow_period','signal_period'] : ['period'];
  if (Object.keys(params).some(key => !allowedParams.includes(key))) return refuse();
  if (type === 'macd' && allowedParams.some((key,index) => (params[key] ?? [12,26,9][index]) !== [12,26,9][index])) return refuse();
  if (!Number.isInteger(period) || period <= 0) return refuse();
  // Save uses this indicator for both rules. Price/close or a different
  // reference cannot be represented and must never silently change on Save.
  const references = new Set([type, type === 'macd' ? 'macd' : `${type}_${period}`]);
  if (indicator.id != null) references.add(`${type}_${indicator.id}`);
  const side = (rule, fallback) => String(rule.signal_type ?? rule.side ?? fallback ?? '').toUpperCase();
  const validRule = (rule, fallback) => references.has(rule.indicator) && typeof rule.value === 'number' && Number.isFinite(rule.value)
    && ['BUY','SELL'].includes(side(rule,fallback))
    && !(rule.side != null && rule.signal_type != null && String(rule.side).toUpperCase() !== String(rule.signal_type).toUpperCase());
  const rule = row.entry_conditions[0], exit = row.exit_conditions[0];
  if (!validRule(rule) || (exit && (!validRule(exit,'SELL') || side(exit,'SELL') !== 'SELL' || !['>','above'].includes(exit.operator)))) return refuse();
  const values = {id:row.id,name:row.name,pair:row.trading_pairs[0],indicator:type,period,
    side:side(rule),operator:({above:'>',below:'<'}[rule.operator] || rule.operator),threshold:rule.value,
    exit_threshold:exit?.value ?? '',risk:row.risk_per_trade_pct,stop:row.stop_loss_pct,take:row.take_profit_pct};
  // Complete validation uses the actual controls before touching any field,
  // including hidden ID. A refused edit leaves the user's entire draft intact.
  for (const [name,value] of Object.entries(values)) {
    const field = f.namedItem(name);
    if (field.tagName === 'SELECT' && ![...field.options].some(option => option.value === String(value))) return refuse();
    if (field.type === 'number' && value !== '') {
      if (typeof value !== 'number' || !Number.isFinite(value) || (field.min !== '' && value < Number(field.min)) || (field.max !== '' && value > Number(field.max))) return refuse();
    }
  }
  for (const [name,value] of Object.entries(values)) f.namedItem(name).value = value;
  f.active.checked = row.is_active;
  form.scrollIntoView({behavior:'smooth'}); message(`Editing ${row.name}. Save applies changes to this strategy.`);
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
  const [signals, decisions] = await Promise.all([api('/api/signals'), api('/api/paper/decisions')]);
  const explanations = {
    shared_pair_exposure: 'A position in this pair was already held by this paper account. Another buy was blocked across its strategies.',
    risk_per_trade_limit: 'The requested size exceeded the allowed risk per trade.',
    max_open_positions: 'The account had reached its maximum number of open positions.',
    user_position_limit: 'The requested position exceeded the account size limit.',
    shared_risk_limits: 'The order did not pass the shared account risk limits.',
    no_owned_position: 'This strategy had no owned position to sell.',
    owned_held_quantity_required: 'A sell must reduce an owned position and stay within its held quantity.',
    invalid_size: 'No valid positive order size was available within the configured limits.',
    signal_entry: 'The signal entry filled.',
    signal_exit: 'The signal exit filled.'
  };
  const linked = new Map();
  for (const decision of decisions) {
    if (decision.signal_id == null) continue;
    if (!linked.has(decision.signal_id)) linked.set(decision.signal_id, []);
    linked.get(decision.signal_id).push(decision);
  }
  const explained = signals.map(signal => {
    const history = (linked.get(signal.id) || []).slice().sort((a,b) => a.id - b.id);
    const latest = history[history.length - 1];
    const reason = latest && latest.reason;
    const explanation = reason ? `${explanations[reason] || 'Recorded decision reason'} (${reason})` :
      signal.status === 'pending' ? 'Awaiting execution.' : 'No linked decision reason was recorded.';
    return {...signal, decision_explanation: explanation, decision_history: history};
  });
  table('signals', explained, [['Signal','id'],['Strategy','strategy_id'],['UTC time','timestamp'],['Pair','trading_pair'],['Side','signal_type'],['Status','status'],['Reason','decision_explanation']], (cell,row) => {
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
