"""Offline public-summary privacy, lifecycle, and fixed-target API contracts."""
import base64
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from trading_stack.paper_status_publisher import (
    BRANCH, GIT_API, GH, Publisher, edit_status, render_summary, utc, worker_alive,
    machine_summary, fingerprint,
)

NOW = 1_800_000_000


def manifest():
    return {'mode': 'paper', 'symbol': 'BTC-USDT', 'pid': 123,
            'started_at': utc(NOW - 60), 'deadline_at': utc(NOW + 1800),
            'config': {'initial_cash': 10000, 'fee_bps': 10, 'slippage_bps': 5}}


def snapshot(**changes):
    result = {'mode': 'paper', 'state': 'running', 'updated_at': utc(NOW),
              'last_candle': utc(NOW - 60), 'mark_price': 50000,
              'decision_count': 3, 'fill_count': 1,
              'economics': {'currency': 'USDT', 'equity': 10001.5, 'cash': 9950,
                            'realized_pnl': 0, 'unrealized_pnl': 1.5, 'fees': .05}}
    result.update(changes)
    return result


class PublisherTests(unittest.TestCase):
    def folder(self):
        root = Path(os.environ.get('TEAKA_TEST_ARTIFACT_ROOT',
                    str(Path(__file__).resolve().parents[1] / 'paper_trading/state/test-artifacts')))
        path = root / ('publisher-' + uuid.uuid4().hex)
        path.mkdir(parents=True, exist_ok=False)
        return path

    def setup_run(self, data=None, info=None):
        path = self.folder()
        (path / 'manifest.json').write_text(json.dumps(info or manifest()), encoding='utf-8')
        (path / 'status-000001.json').write_text(json.dumps(data or snapshot()), encoding='utf-8')
        return path

    def test_renderer_whitelist_pnl_and_disclosures(self):
        info = manifest()
        info.update(output='/PRIVATE/secret', api_key='secret_key', pid=987654321)
        data = snapshot(error='DO NOT PUBLISH secret_token', source='https://private/account',
                        position={'account_id': 'hidden'}, event={'password': 'hidden'})
        text, final = render_summary(info, data, now=NOW, alive=True, next_refresh=NOW + 900)
        self.assertFalse(final)
        for private in ('PRIVATE', 'secret', '987654321', 'account_id', 'password', 'hidden'):
            self.assertNotIn(private, text)
        self.assertIn('Total PnL | +1.5000', text)
        self.assertIn('5 bps slippage', text)
        self.assertIn('10 bps fees', text)
        self.assertIn('not a live tick', text)
        self.assertIn('Status: Running', text)
        data = machine_summary(info, data, text, now=NOW, terminal=False, generation='safe_generation')
        encoded = json.dumps(data)
        for private in ('PRIVATE', 'secret', '987654321', 'account_id', 'password', 'hidden'):
            self.assertNotIn(private, encoded)
        self.assertTrue(all(not isinstance(v, (dict, list)) for v in data.values()))

    def test_invalid_free_text_states_numbers_and_dates_never_render(self):
        for data in (snapshot(state='SECRET'), snapshot(updated_at='SECRET'),
                     snapshot(fill_count=True), snapshot(mark_price=float('nan')),
                     snapshot(economics=dict(snapshot()['economics'], equity=float('inf')))):
            with self.assertRaises((ValueError, TypeError)):
                render_summary(manifest(), data, now=NOW, alive=True, next_refresh=NOW + 900)

    def test_stale_dead_final_and_unverified_liveness(self):
        cases = [
            (snapshot(updated_at=utc(NOW - 181)), True, 'Stale', False),
            (snapshot(), False, 'Stopped unexpectedly', True),
            (snapshot(state='completed'), False, 'Completed', True),
            (snapshot(state='failed'), True, 'runtime failure', True),
            (snapshot(), None, 'could not be verified', False),
        ]
        for data, alive, expected, terminal in cases:
            with self.subTest(expected=expected):
                text, final = render_summary(manifest(), data, now=NOW, alive=alive, next_refresh=NOW + 900)
                self.assertIn(expected, text)
                self.assertEqual(final, terminal)

    def test_bound_ends_monitoring_even_worker_still_alive(self):
        text, final = render_summary(manifest(), snapshot(), now=NOW + 2100,
                                     alive=True, next_refresh=NOW + 3000)
        self.assertTrue(final)
        self.assertIn('Monitoring ended', text)
        self.assertIn('No further scheduled updates', text)

    def test_one_shot_preserves_immutable_artifacts(self):
        run = self.setup_run()
        posted = []
        publisher = Publisher(run, wall=lambda: NOW, liveness=lambda *_: True,
                              edit=lambda path, _: posted.append(path.read_text()) or {'published': True})
        result = publisher.run(once=True)
        self.assertTrue(result['published'])
        self.assertEqual(len(posted), 1)
        self.assertIsNone(result['next_refresh_at'])
        self.assertTrue((publisher.output / 'body-000001.md').exists())
        self.assertTrue((publisher.output / 'status-000001.json').exists())
        self.assertEqual(len(list(run.glob('status-*.json'))), 1)
        self.assertEqual(json.loads((run / 'status-000001.json').read_text()), snapshot())

    def test_cadence_and_deadline_final_publish(self):
        run = self.setup_run()
        clock = [NOW]
        times = []
        def sleep(seconds):
            clock[0] += seconds
        publisher = Publisher(run, wall=lambda: clock[0], sleep=sleep,
                              liveness=lambda *_: True,
                              edit=lambda *_: times.append(clock[0]) or {'published': True})
        result = publisher.run()
        self.assertEqual(times, [NOW, NOW + 210, NOW + 1800])
        self.assertEqual(result['state'], 'final')

    def test_final_file_preferred_and_no_worker_mutations(self):
        run = self.setup_run()
        final = snapshot(state='stopped')
        (run / 'final-status.json').write_text(json.dumps(final), encoding='utf-8')
        publisher = Publisher(run, wall=lambda: NOW, liveness=lambda *_: False, edit=lambda *_: {'published': True})
        result = publisher.run()
        self.assertEqual(result['state'], 'final')
        self.assertIn('Status: Stopped', (publisher.output / 'body-000001.md').read_text())
        self.assertEqual(publisher.sequence, 1)

    def test_malformed_snapshot_publishes_safe_notice_only(self):
        run = self.setup_run(snapshot(state='PRIVATE_PASSWORD'))
        publisher = Publisher(run, wall=lambda: NOW, liveness=lambda *_: True, edit=lambda *_: {'published': True})
        result = publisher.run(once=True)
        text = (publisher.output / 'body-000001.md').read_text()
        self.assertNotIn('PRIVATE_PASSWORD', text)
        self.assertNotIn(str(run), text)
        self.assertIn('temporarily unavailable', text)
        self.assertEqual(result['error'], 'snapshot_validation_failed')

    def test_transport_atomic_two_files_one_commit_fastforward_only(self):
        folder = self.folder()
        body = folder / 'body.md'
        body.write_text('Safe paper summary', encoding='utf-8')
        machine = folder / 'machine.json'
        machine.write_text('{"mode":"paper"}', encoding='utf-8')
        responses = [{'object': {'sha': 'a' * 40}}, {'tree': {'sha': 'b' * 40}},
                     {'sha': 'c' * 40}, {'sha': 'd' * 40}, {'object': {'sha': 'd' * 40}}]
        with patch('trading_stack.paper_status_publisher.subprocess.run', side_effect=[
            SimpleNamespace(returncode=0, stdout='HTTP/2.0 200 OK\n\n' + json.dumps(item)) for item in responses
        ]) as call:
            self.assertTrue(edit_status(body, machine)['published'])
            self.assertEqual(call.call_count, 5)
            first, second, third, fourth, fifth = call.call_args_list
            self.assertEqual(first.args[0], [GH, 'api', '--include', '--method', 'GET', GIT_API + '/ref/heads/paper-status'])
            tree = json.loads(Path(third.args[0][-1]).read_text())
            self.assertEqual(tree['base_tree'], 'b' * 40)
            self.assertEqual([entry['path'] for entry in tree['tree']], ['README.md', 'status.json'])
            self.assertEqual(tree['tree'][0]['content'], 'Safe paper summary')
            commit = json.loads(Path(fourth.args[0][-1]).read_text())
            self.assertEqual(commit['parents'], ['a' * 40])
            self.assertEqual(commit['tree'], 'c' * 40)
            update = json.loads(Path(fifth.args[0][-1]).read_text())
            self.assertEqual(update, {'sha': 'd' * 40, 'force': False})
            self.assertIn(GIT_API + '/refs/heads/paper-status', fifth.args[0])
            self.assertEqual(fifth.kwargs['timeout'], 30)
            self.assertTrue(fifth.kwargs['capture_output'])

    def test_transport_no_write_after_bad_remote_or_get_failure(self):
        for result in (SimpleNamespace(returncode=1, stdout='SECRET'),
                       SimpleNamespace(returncode=0, stdout='{"sha":"bad","path":"README.md","type":"file"}')):
            with patch('trading_stack.paper_status_publisher.subprocess.run', return_value=result) as call:
                self.assertFalse(edit_status(self.folder() / 'unused.md', 'unused.json')['published'])
                self.assertEqual(call.call_count, 1)

    def test_changes_only_normalized_waiting_and_new_candle_throttle(self):
        run = self.setup_run()
        clock = [NOW]
        posted = []
        publisher = Publisher(run, wall=lambda: clock[0], liveness=lambda *_: True,
                              edit=lambda *_: posted.append(clock[0]) or {'published': True})
        publisher.tick()
        clock[0] += 30
        (run / 'status-000002.json').write_text(json.dumps(snapshot(state='waiting_for_candle', updated_at=utc(clock[0]))))
        self.assertEqual(publisher.tick()['skipped'], 'unchanged')
        (run / 'status-000003.json').write_text(json.dumps(snapshot(updated_at=utc(clock[0]), last_candle=utc(NOW), decision_count=4)))
        self.assertEqual(publisher.tick()['skipped'], 'publication_throttle')
        clock[0] += 30
        self.assertTrue(publisher.tick()['published'])
        self.assertEqual(posted, [NOW, NOW + 60])
        machine = json.loads((publisher.output / 'public-status-000004.json').read_text())
        self.assertIn(machine['generation_id'], (publisher.output / 'body-000004.md').read_text())
        clock[0] += 1
        (run / 'final-status.json').write_text(json.dumps(snapshot(state='completed', updated_at=utc(clock[0]))))
        self.assertTrue(publisher.tick()['published'])

    def test_backoff_honors_retry_after_and_reset_without_secret_output(self):
        with patch('trading_stack.paper_status_publisher.time.time', return_value=NOW), patch(
                'trading_stack.paper_status_publisher.subprocess.run', return_value=SimpleNamespace(
                    returncode=1, stdout=f'HTTP/2.0 429 Too Many\nRetry-After: 120\nX-RateLimit-Remaining: 0\nX-RateLimit-Reset: {NOW + 600}\n\nSECRET')):
            result = edit_status(self.folder() / 'unused.md', 'unused.json')
            self.assertFalse(result['published'])
            self.assertEqual(result['retry_after'], 600)
        clock = [NOW]
        attempts = []
        publisher = Publisher(self.setup_run(), wall=lambda: clock[0], liveness=lambda *_: True,
            edit=lambda *_: attempts.append(clock[0]) or {'published': False, 'retry_after': 600})
        publisher.tick()
        clock[0] += 30
        self.assertEqual(publisher.tick()['skipped'], 'backoff')
        clock[0] = NOW + 600
        publisher.tick()
        self.assertEqual(attempts, [NOW, NOW + 600])

    def test_process_check_only_returns_boolean_and_checks_identity(self):
        for response, expected in [('true', True), ('false', False), ('SECRET COMMAND', None)]:
            with patch('trading_stack.paper_status_publisher.subprocess.run',
                       return_value=SimpleNamespace(returncode=0, stdout=response)) as call:
                self.assertIs(worker_alive(123, self.folder()), expected)
                command = call.call_args.args[0]
                self.assertIn('-EncodedCommand', command)
                self.assertTrue(Path(command[0]).is_absolute())
                script = base64.b64decode(command[-1]).decode('utf-16le')
                self.assertIn('ProcessId = 123', script)
                self.assertIn('overnight_paper', script)
                self.assertIn('ConvertTo-Json -InputObject ([bool]$paperMatch)', script)

    def test_future_manifest_rejected_and_huge_retry_clamped_to_bound(self):
        info = manifest()
        info['started_at'], info['deadline_at'] = utc(NOW + 61), utc(NOW + 1000)
        with self.assertRaisesRegex(ValueError, 'future_run_start'):
            Publisher(self.setup_run(info=info), wall=lambda: NOW)
        clock = [NOW]
        attempts = []
        publisher = Publisher(self.setup_run(), wall=lambda: clock[0], liveness=lambda *_: True,
            edit=lambda *_: attempts.append(clock[0]) or {'published': False, 'retry_after': 1e300})
        publisher.tick()
        self.assertEqual(publisher.retry_at, publisher.bound)
        clock[0] = publisher.bound
        self.assertEqual(publisher.tick()['skipped'], 'deadline')
        self.assertEqual(attempts, [NOW])


if __name__ == '__main__':
    unittest.main()
