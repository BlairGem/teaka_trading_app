from __future__ import annotations

import os
import sys
import unittest
import uuid
from pathlib import Path


WORKTREE = Path(__file__).resolve().parents[1]
ARTIFACT_PARENT = WORKTREE / "paper_trading" / "state" / "test-artifacts"
ARTIFACT_PARENT.mkdir(parents=True, exist_ok=True)
ARTIFACT_ROOT = ARTIFACT_PARENT / f"run-{uuid.uuid4().hex}"
ARTIFACT_ROOT.mkdir(exist_ok=False)
os.environ["TEAKA_TEST_ARTIFACT_ROOT"] = str(ARTIFACT_ROOT)
sys.dont_write_bytecode = True


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
    if path is None or (path != ARTIFACT_ROOT and ARTIFACT_ROOT not in path.parents):
        raise RuntimeError(f"offline test blocked {event} outside {ARTIFACT_ROOT}")


def _audit_guard(event: str, args: tuple[object, ...]) -> None:
    if (
        event.startswith("socket.")
        or event == "subprocess.Popen"
        or event == "os.system"
        or event == "os.startfile"
        or event.startswith("os.spawn")
        or event.startswith("os.exec")
    ):
        raise RuntimeError(f"offline test blocked {event}")

    if event == "open":
        path, mode, flags = args
        writes = isinstance(mode, str) and any(flag in mode for flag in "wax+")
        if isinstance(flags, int):
            write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            writes = writes or bool(flags & write_flags)
        if writes:
            _require_artifact_path(path, event)
    elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.unlink", "os.symlink"}:
        _require_artifact_path(args[0], event)
    elif event in {"os.rename", "os.replace", "os.link"}:
        _require_artifact_path(args[0], event)
        _require_artifact_path(args[1], event)


sys.addaudithook(_audit_guard)
sys.path.insert(0, str(WORKTREE))
sys.path.insert(0, str(WORKTREE / "paper_trading"))


def main() -> int:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite(
        (
            loader.loadTestsFromName("paper_trading.test_paper_broker"),
            loader.loadTestsFromName("tests.test_paper_accounting"),
        )
    )
    print(f"Preserved test artifacts: {ARTIFACT_ROOT}")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
