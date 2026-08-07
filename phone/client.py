"""
Phone / Termux Python client for TeAka.

Run on a phone that has Python (Termux, Pydroid, etc.):

    python phone/client.py status
    python phone/client.py paper
    python phone/client.py command ping

Set TEAKA_HOST to your PC/server LAN IP or tunnel URL, e.g.:

    export TEAKA_HOST=http://192.168.1.20:5050
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def _host_from_env() -> str:
    return os.environ.get("TEAKA_HOST", "http://127.0.0.1:5050")


def _request(host: str, method: str, path: str, body: dict | None = None) -> dict:
    url = host.rstrip("/") + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Cannot reach TeAka at {url} ({exc.reason}). "
            "Start connect_python.py on the host and set TEAKA_HOST."
        ) from exc


def cmd_status(host: str) -> None:
    print(json.dumps(_request(host, "GET", "/api/phone/status"), indent=2))


def cmd_paper(host: str) -> None:
    print(json.dumps(_request(host, "POST", "/api/phone/paper-run", {}), indent=2))


def cmd_command(host: str, command: str) -> None:
    print(
        json.dumps(
            _request(host, "POST", "/api/phone/command", {"command": command}),
            indent=2,
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="TeAka phone Python client")
    parser.add_argument(
        "--host",
        default=_host_from_env(),
        help="TeAka host base URL (or set TEAKA_HOST)",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("status", help="Fetch host status")
    sub.add_parser("paper", help="Trigger a paper sample run on the host")
    p_cmd = sub.add_parser("command", help="Send a remote command")
    p_cmd.add_argument("command", help="Command name, e.g. ping or status_check")

    args = parser.parse_args(argv)
    if args.action == "status":
        cmd_status(args.host)
    elif args.action == "paper":
        cmd_paper(args.host)
    elif args.action == "command":
        cmd_command(args.host, args.command)
    else:
        parser.error(f"unknown action {args.action}")


if __name__ == "__main__":
    main()
