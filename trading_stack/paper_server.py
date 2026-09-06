"""Reusable single-process loopback entrypoint for finite paper sessions."""
import argparse
from pathlib import Path
from .app import create_app


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--output-root', required=True, type=Path)
    parser.add_argument('--port', type=int, default=5067, help='Loopback port; 0 selects a free port')
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    return args


def build_app(args):
    roots = [root.resolve(strict=True) for root in (args.data_root, args.output_root) if root.exists()]
    if len(roots) != 2 or not all(root.is_dir() for root in roots):
        raise ValueError('Both data and output roots must be existing directories')
    return create_app({'PAPER_DATA_ROOT': str(roots[0]), 'PAPER_OUTPUT_ROOT': str(roots[1]),
                       'DEBUG': False, 'SESSION_COOKIE_SAMESITE': 'Strict'})


def main(argv=None):
    from werkzeug.serving import make_server
    args = parse_args(argv)
    app = build_app(args)
    # No reloader, scheduler, threading, persistent DB or external host binding.
    server = make_server('127.0.0.1', args.port, app, threaded=False, processes=1)
    print(f'PAPER_URL=http://127.0.0.1:{server.server_port}', flush=True)
    print('Memory-only paper session. Stop with Ctrl+C; accounts and session state are lost.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
