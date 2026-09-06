"""Publish changed PAPER snapshots atomically to a dedicated GitHub branch."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

REPO = 'BlairGem1234/teaka_trading_app'
GH = shutil.which('gh') or 'gh'
BRANCH = 'paper-status'
GIT_API = f'repos/{REPO}/git'
STATES = {'starting', 'running', 'waiting_for_candle', 'order_intent',
          'paused_stale', 'retrying', 'completed', 'stopped', 'failed'}
FINAL = {'completed', 'stopped', 'failed'}


def number(value, *, minimum=None, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('invalid_numeric_field')
    if minimum is not None and value < minimum or integer and int(value) != value:
        raise ValueError('invalid_numeric_field')
    return value


def stamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('invalid_timestamp')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ValueError('invalid_timestamp')
        return dt.timestamp()
    except (ValueError, OverflowError):
        raise ValueError('invalid_timestamp') from None


def utc(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec='seconds')


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get('mode') != 'paper' or manifest.get('symbol') != 'BTC-USDT':
        raise ValueError('invalid_manifest')
    if not isinstance(manifest.get('config'), dict):
        raise ValueError('invalid_manifest')
    initial = number(manifest['config']['initial_cash'], minimum=0)
    if manifest['config'].get('fee_bps') != 10 or manifest['config'].get('slippage_bps') != 5:
        raise ValueError('unexpected_economics_model')
    started, deadline = stamp(manifest['started_at']), stamp(manifest['deadline_at'])
    number(manifest['pid'], minimum=1, integer=True)
    if not 0 < deadline - started <= 8 * 3600 + 1:
        raise ValueError('invalid_deadline')
    return initial, deadline


def worker_alive(pid, run_dir):
    """Read only process identity; never return the command line to callers."""
    number(pid, minimum=1, integer=True)
    encoded = base64.b64encode(str(Path(run_dir).resolve()).encode('utf-8')).decode('ascii')
    script = (
        "$ErrorActionPreference='Stop'; "
        f"$paperPath=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}')); "
        f"$paperProcess=Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}'; "
        "$paperMatch=($null -ne $paperProcess -and "
        "$paperProcess.CommandLine -match '(?i)(?:^|\\s)-m\\s+trading_stack\\.overnight_paper(?:\\s|$)' -and "
        "$paperProcess.CommandLine -match ([regex]::Escape($paperPath)+'(?:\"|\\s|$)')); "
        'ConvertTo-Json -InputObject ([bool]$paperMatch) -Compress'
    )
    try:
        executable = shutil.which('powershell.exe') or shutil.which('pwsh.exe')
        if executable is None:
            return None
        encoded_script = base64.b64encode(script.encode('utf-16le')).decode('ascii')
        result = subprocess.run([executable, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded_script],
                                capture_output=True, text=True, timeout=20, check=False,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode or result.stdout.strip() not in ('true', 'false'):
            return None
        return result.stdout.strip() == 'true'
    except (OSError, subprocess.SubprocessError):
        return None


def render_summary(manifest, snapshot, *, now, alive, next_refresh):
    """Build public text from validated scalar fields only; never echo free text."""
    initial, deadline = validate_manifest(manifest)
    if not isinstance(snapshot, dict) or snapshot.get('mode') != 'paper' or snapshot.get('state') not in STATES:
        raise ValueError('invalid_snapshot')
    observed = stamp(snapshot['updated_at'])
    if observed > now + 60:
        raise ValueError('future_snapshot')
    candle = stamp(snapshot['last_candle']) if snapshot.get('last_candle') is not None else None
    if candle is not None and candle > now:
        raise ValueError('future_candle')
    economics = snapshot['economics']
    if not isinstance(economics, dict):
        raise ValueError('invalid_economics')
    if economics.get('currency') != 'USDT':
        raise ValueError('unexpected_currency')
    equity = number(economics['equity'], minimum=0)
    cash = number(economics['cash'], minimum=0)
    fees = number(economics['fees'], minimum=0)
    realized = number(economics['realized_pnl'])
    unrealized = number(economics['unrealized_pnl'])
    decisions = int(number(snapshot['decision_count'], minimum=0, integer=True))
    fills = int(number(snapshot['fill_count'], minimum=0, integer=True))
    mark = snapshot.get('mark_price')
    if mark is not None:
        number(mark, minimum=0)
    raw_state = snapshot['state']
    terminal = raw_state in FINAL or alive is False or now >= deadline + 300
    if raw_state in FINAL:
        state = {'completed': 'Completed', 'stopped': 'Stopped', 'failed': 'Stopped after a data or runtime failure'}[raw_state]
    elif alive is False:
        state = 'Stopped unexpectedly; no final worker snapshot'
    elif now >= deadline + 300:
        state = 'Monitoring ended at its deadline; worker completion unconfirmed'
    elif now >= deadline:
        state = 'Run deadline reached; awaiting final worker snapshot'
    elif alive is None:
        state = 'Worker identity could not be verified'
    elif now - observed > 180 or raw_state in ('paused_stale', 'retrying') or (candle is not None and now - candle - 60 > 180):
        state = 'Stale or unavailable market data; paper trading status needs attention'
    elif raw_state == 'starting':
        state = 'Starting; awaiting first completed candle'
    else:
        state = 'Running'
    refresh = 'No further scheduled updates' if terminal or next_refresh is None else utc(next_refresh)
    lines = [
        '# BTC/USDT PAPER practice', '', f'**Status: {state}**', '',
        f'- Published UTC: {utc(now)}', f'- Worker snapshot observed UTC: {utc(observed)}',
        f'- Last processed candle start UTC: {utc(candle) if candle is not None else "Not available yet"}',
        f'- Run deadline UTC: {utc(deadline)}', f'- Next local check UTC: {refresh}', '',
        '| Virtual metric | USDT |', '|---|---:|',
        f'| Initial equity | {initial:.4f} |', f'| Current equity | {equity:.4f} |',
        f'| Total PnL | {equity - initial:+.4f} |', f'| Realized PnL | {realized:+.4f} |',
        f'| Unrealized PnL | {unrealized:+.4f} |', f'| Cash | {cash:.4f} |',
        f'| Fees charged | {fees:.4f} |', '',
        f'Paper decisions: **{decisions}**. Simulated fills: **{fills}**.', '',
    ]
    if mark is not None:
        lines += [f'Latest simulated mark: **{mark:.4f} USDT**. This is not a live tick.', '']
    lines += [
        'Real public Kraken one-minute candles; simulated paper execution only. '
        'Unvalidated 20-period SMA practice strategy, long-only, with a 50 USDT entry cap.', '',
        'Signals use the prior completed candle. Fills simulate the following candle open after '
        'that candle completes; protective exits use its OHLC range. '
        'Fixed 10 bps fees and 5 bps slippage proxy; spread is not separately modeled. '
        'These are practice approximations, not brokerage-equivalent execution.', '',
        'Held exposure remains marked at the last valid candle when the run stops; no artificial liquidation. '
        'If the published timestamp stops advancing, treat this page as stale.',
        'New meaningful one-minute snapshots normally publish at most once per minute; unchanged checks are skipped. '
        'GitHub caching may delay visibility. Another chat or reader must poll the stable status URL for updates.',
    ]
    return '\n'.join(lines) + '\n', terminal


class ApiFailure(Exception):
    def __init__(self, retry_after=60):
        self.retry_after = retry_after


def api(method, endpoint, folder, payload=None):
    command = [GH, 'api', '--include', '--method', method, endpoint]
    if payload is not None:
        request_path = Path(folder) / ('request-' + uuid.uuid4().hex + '.json')
        with request_path.open('x', encoding='utf-8') as handle:
            json.dump(payload, handle, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        command += ['--input', str(request_path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    header, separator, body = result.stdout.replace('\r\n', '\n').partition('\n\n')
    if not separator:
        raise ApiFailure()
    match = re.match(r'HTTP/\S+\s+(\d{3})', header)
    if not match:
        raise ApiFailure()
    status = int(match.group(1))
    if result.returncode or not 200 <= status < 300:
        headers = dict(line.lower().split(':', 1) for line in header.splitlines()[1:] if ':' in line)
        retry = 60
        try:
            retry = max(retry, float(headers.get('retry-after', '0')))
            if headers.get('x-ratelimit-remaining', '').strip() == '0':
                retry = max(retry, float(headers.get('x-ratelimit-reset', '0')) - time.time())
        except ValueError:
            pass
        raise ApiFailure(retry if math.isfinite(retry) else 900)
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ApiFailure()
    return value


def valid_sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ApiFailure()
    return value


def edit_status(body_file, status_file):
    """One commit containing both files; only a fast-forward ref update is allowed."""
    try:
        body_file = Path(body_file)
        folder = body_file.parent
        head = valid_sha(api('GET', GIT_API + '/ref/heads/' + BRANCH, folder)['object']['sha'])
        tree = valid_sha(api('GET', GIT_API + '/commits/' + head, folder)['tree']['sha'])
        entries = [{'path': name, 'mode': '100644', 'type': 'blob', 'content': path.read_text(encoding='utf-8')}
                   for name, path in [('README.md', body_file), ('status.json', Path(status_file))]]
        tree_sha = valid_sha(api('POST', GIT_API + '/trees', folder, {'base_tree': tree, 'tree': entries})['sha'])
        commit = valid_sha(api('POST', GIT_API + '/commits', folder,
                              {'message': 'Refresh sanitized PAPER practice snapshot',
                               'tree': tree_sha, 'parents': [head]})['sha'])
        api('PATCH', GIT_API + '/refs/heads/' + BRANCH, folder, {'sha': commit, 'force': False})
        return {'published': True, 'retry_after': 0}
    except ApiFailure as exc:
        return {'published': False, 'retry_after': exc.retry_after}
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError):
        return {'published': False, 'retry_after': 60}


def machine_summary(manifest, snapshot, body, *, now, terminal, generation):
    # render_summary already validated all selected fields. All other source
    # fields (including errors, paths, identity, and event text) are discarded.
    economics = snapshot['economics']
    return {'generation_id': generation, 'mode': 'paper', 'symbol': 'BTC-USDT',
            'state': body.split('**Status: ', 1)[1].split('**', 1)[0],
            'terminal': terminal, 'published_at': utc(now),
            'observed_at': utc(stamp(snapshot['updated_at'])),
            'candle_start_at': utc(stamp(snapshot['last_candle'])) if snapshot.get('last_candle') else None,
            'deadline_at': utc(stamp(manifest['deadline_at'])),
            'initial_equity_usdt': manifest['config']['initial_cash'],
            'equity_usdt': economics['equity'], 'cash_usdt': economics['cash'],
            'total_pnl_usdt': economics['equity'] - manifest['config']['initial_cash'],
            'realized_pnl_usdt': economics['realized_pnl'], 'unrealized_pnl_usdt': economics['unrealized_pnl'],
            'fees_usdt': economics['fees'], 'decision_count': snapshot['decision_count'],
            'fill_count': snapshot['fill_count'], 'simulated_mark_usdt': snapshot.get('mark_price'),
            'fee_bps': 10, 'slippage_bps': 5, 'execution': 'delayed_candle_simulation',
            'strategy': 'unvalidated_sma20_long_only'}


def fingerprint(data):
    stable = {k: v for k, v in data.items() if k not in ('generation_id', 'published_at', 'observed_at')}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, allow_nan=False).encode()).hexdigest()


def read_json(path):
    if path.stat().st_size > 2_000_000:
        raise ValueError('oversized_input')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('invalid_input')
    return value


class Publisher:
    def __init__(self, run_dir, *, interval_seconds=30, wall=time.time,
                 sleep=time.sleep, liveness=worker_alive, edit=edit_status):
        self.run_dir = Path(run_dir).resolve(strict=True)
        self.interval = number(interval_seconds, minimum=15)
        if self.interval > 60:
            raise ValueError('interval_too_large')
        self.manifest = read_json(self.run_dir / 'manifest.json')
        _, deadline = validate_manifest(self.manifest)
        if stamp(self.manifest['started_at']) > wall() + 60:
            raise ValueError('future_run_start')
        self.bound = deadline + 300
        self.wall, self.sleep, self.liveness, self.edit = wall, sleep, liveness, edit
        self.output = self.run_dir / ('github-publisher-' + uuid.uuid4().hex)
        self.output.mkdir(exist_ok=False)
        self.sequence = 0
        self.last_fingerprint = None
        self.last_state = None
        self.last_published = -math.inf
        self.failures = 0
        self.retry_at = 0
        self.write('manifest.json', json.dumps({'branch': BRANCH, 'repo': REPO,
                   'started_at': utc(wall()), 'deadline_at': utc(self.bound),
                   'interval_seconds': self.interval}, indent=2))

    def write(self, name, content):
        path = self.output / name
        with path.open('x', encoding='utf-8') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return path

    def latest(self):
        final = self.run_dir / 'final-status.json'
        if final.exists():
            return read_json(final)
        files = sorted(p for p in self.run_dir.glob('status-*.json')
                       if re.fullmatch(r'status-\d{6}\.json', p.name))
        if not files:
            raise ValueError('missing_snapshot')
        # A worker may still be fsyncing its exclusive new snapshot. Retry at
        # the next publication rather than silently presenting an older one.
        return read_json(files[-1])

    def tick(self, *, once=False):
        self.sequence += 1
        now = self.wall()
        next_refresh = min(now + self.interval, self.bound)
        error = None
        terminal = False
        generation = uuid.uuid4().hex
        try:
            snapshot = self.latest()
            alive = self.liveness(self.manifest['pid'], self.run_dir)
            body, terminal = render_summary(self.manifest, snapshot, now=now, alive=alive,
                                           next_refresh=None if once else next_refresh)
            data = machine_summary(self.manifest, snapshot, body, now=now, terminal=terminal, generation=generation)
        except (ValueError, KeyError, TypeError, OSError, OverflowError):
            error = 'snapshot_validation_failed'
            terminal = now >= self.bound
            body = ('# BTC/USDT PAPER practice\n\n**Status: Summary temporarily unavailable**\n\n'
                    f'Published UTC: {utc(now)}\n\n'
                    'The latest local snapshot could not be safely validated. '
                    'Previous values must be treated as stale. No account or local diagnostic details are published.\n')
            data = {'generation_id': generation, 'mode': 'paper', 'symbol': 'BTC-USDT',
                    'state': 'Summary temporarily unavailable', 'terminal': terminal, 'published_at': utc(now)}
        signature = fingerprint(data)
        published = False
        skipped = None
        if now >= self.bound:
            terminal = True
            skipped = 'deadline'
        elif now < self.retry_at:
            skipped = 'backoff'
        elif signature == self.last_fingerprint:
            skipped = 'unchanged'
        elif now - self.last_published < 60 and not terminal and data['state'] == self.last_state:
            skipped = 'publication_throttle'
        else:
            body += '\nSnapshot generation: `' + generation + '`\n'
            path = self.write(f'body-{self.sequence:06d}.md', body)
            machine_path = self.write(f'public-status-{self.sequence:06d}.json', json.dumps(data, indent=2, allow_nan=False))
            outcome = self.edit(path, machine_path)
            published = bool(outcome['published'])
            if published:
                self.last_fingerprint, self.last_state, self.last_published = signature, data['state'], now
                self.failures = 0
            else:
                self.failures += 1
                retry = outcome.get('retry_after', 60)
                if not isinstance(retry, (int, float)) or not math.isfinite(retry):
                    retry = 900
                self.retry_at = min(self.bound, now + max(min(900, 60 * 2 ** min(self.failures - 1, 4)), retry))
                error = 'github_update_failed'
        state = 'final' if terminal else 'monitoring'
        result = {'state': state, 'updated_at': utc(now), 'branch': BRANCH,
                  'published': published, 'skipped': skipped, 'error': error,
                  'retry_at': utc(self.retry_at) if self.retry_at > now else None,
                  'next_refresh_at': None if terminal or once else utc(next_refresh)}
        self.write(f'status-{self.sequence:06d}.json', json.dumps(result, indent=2))
        return result

    def run(self, *, once=False):
        while True:
            if (self.output / 'STOP').exists():
                return {'state': 'publisher_stopped', 'published': False}
            result = self.tick(once=once)
            if once or result['state'] == 'final' and (result['published'] or result['skipped'] == 'unchanged') or self.wall() >= self.bound:
                return result
            wake = min(stamp(result['next_refresh_at']) if result['next_refresh_at'] else self.wall() + self.interval,
                       self.bound)
            while self.wall() < wake and not (self.output / 'STOP').exists():
                self.sleep(min(1, wake - self.wall()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--interval-seconds', type=int, default=30)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args(argv)
    try:
        publisher = Publisher(args.run_dir, interval_seconds=args.interval_seconds)
        result = publisher.run(once=args.once)
    except (ValueError, KeyError, TypeError, OSError, OverflowError):
        print('Paper status publisher could not validate its local inputs.')
        return 1
    print(json.dumps(result))
    return 0 if result.get('published') else 1


if __name__ == '__main__':
    raise SystemExit(main())
