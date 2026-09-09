from __future__ import annotations

import os
import sys
import unittest
import uuid
import importlib
from pathlib import Path


WORKTREE = Path(__file__).resolve().parents[1]
ARTIFACT_PARENT = WORKTREE / "paper_trading" / "state" / "test-artifacts"
ARTIFACT_ROOT = (
    Path(value).resolve(strict=False)
    if (value := os.environ.get("TEAKA_TEST_ARTIFACT_ROOT"))
    else None
)
_HOSTNAME_METADATA_ALLOWED = False

DENIED_FILE_MUTATIONS = frozenset(
    {
        "os.chflags",
        "os.chmod",
        "os.chown",
        "os.ftruncate",
        "os.lchflags",
        "os.lchmod",
        "os.lchown",
        "os.link",
        "os.remove",
        "os.removexattr",
        "os.rename",
        "os.replace",
        "os.rmdir",
        "os.setxattr",
        "os.symlink",
        "os.truncate",
        "os.unlink",
        "os.utime",
    }
)


def _resolved_path(value: object) -> Path | None:
    if isinstance(value, int):
        return None
    if isinstance(value, bytes):
        value = os.fsdecode(value)
    if not isinstance(value, str):
        return None
    path = Path(value)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve(strict=False)


def _require_artifact_path(value: object, event: str) -> None:
    path = _resolved_path(value)
    if (
        ARTIFACT_ROOT is None
        or path is None
        or (path != ARTIFACT_ROOT and ARTIFACT_ROOT not in path.parents)
    ):
        raise RuntimeError(f"offline test blocked {event} outside {ARTIFACT_ROOT}")


def _audit_guard(event: str, args: tuple[object, ...]) -> None:
    if event == "sqlite3.connect" and args[0] != ":memory:":
        raise RuntimeError("offline test blocked non-memory sqlite database")
    if event == "socket.gethostname" and _HOSTNAME_METADATA_ALLOWED:
        return
    if (
        event.startswith("socket.")
        or event == "subprocess.Popen"
        or event == "os.system"
        or event == "os.startfile"
        or event.startswith("os.spawn")
        or event.startswith("os.exec")
    ):
        raise RuntimeError(f"offline test blocked {event}")

    if event in DENIED_FILE_MUTATIONS:
        raise RuntimeError(f"offline test blocked {event}")

    if event == "open":
        path, mode, flags = args
        writes = isinstance(mode, str) and any(flag in mode for flag in "wax+")
        if isinstance(flags, int):
            write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            writes = writes or bool(flags & write_flags)
        if writes:
            _require_artifact_path(path, event)
    elif event == "os.mkdir":
        _require_artifact_path(args[0], event)


def _install_guard_then_import_numerics(
    add_guard=sys.addaudithook, import_module=importlib.import_module
) -> None:
    global _HOSTNAME_METADATA_ALLOWED

    add_guard(_audit_guard)
    # Python 3.12's Windows platform metadata may fall back from WMI to a
    # command. Suppress only that fallback so its native getwindowsversion
    # path is used instead; all process/file audit rules remain active.
    import platform
    original_syscmd_ver = platform._syscmd_ver if sys.platform == 'win32' else None
    _HOSTNAME_METADATA_ALLOWED = True
    try:
        if original_syscmd_ver is not None:
            platform._syscmd_ver = lambda system='', release='', version='', **_: (system, release, version)
        try:
            import_module("numpy")
            import_module("pandas")
        except ModuleNotFoundError:
            pass
    finally:
        if original_syscmd_ver is not None:
            platform._syscmd_ver = original_syscmd_ver
        _HOSTNAME_METADATA_ALLOWED = False


def main() -> int:
    global ARTIFACT_ROOT

    ARTIFACT_PARENT.mkdir(parents=True, exist_ok=True)
    ARTIFACT_ROOT = ARTIFACT_PARENT / f"run-{uuid.uuid4().hex}"
    ARTIFACT_ROOT.mkdir(exist_ok=False)
    os.environ["TEAKA_TEST_ARTIFACT_ROOT"] = str(ARTIFACT_ROOT)
    sys.dont_write_bytecode = True
    # Pandas asks Windows for hostname metadata during import. The guard allows
    # only that local metadata event; socket creation/connect remains denied.
    _install_guard_then_import_numerics()
    sys.path.insert(0, str(WORKTREE))
    sys.path.insert(0, str(WORKTREE / "paper_trading"))

    loader = unittest.defaultTestLoader
    requested = sys.argv[1:]
    test_names = requested or [
        "paper_trading.test_paper_broker",
        "tests.test_paper_accounting",
        "tests.test_offline_guard",
        "tests.test_strategy_contracts",
        "tests.test_full_paper_integration",
        "tests.test_paper_ui",
        "tests.test_overnight_paper",
        "tests.test_paper_status_publisher",
    ]
    suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in test_names)
    print(f"Preserved test artifacts: {ARTIFACT_ROOT}")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
