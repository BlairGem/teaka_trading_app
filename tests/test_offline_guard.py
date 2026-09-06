from __future__ import annotations

import os
import unittest
import uuid
from pathlib import Path

from tests import run_offline


def artifact_root() -> Path:
    if run_offline.ARTIFACT_ROOT is None:
        raise RuntimeError("offline guard tests must run through tests/run_offline.py")
    return run_offline.ARTIFACT_ROOT


class OfflineGuardTests(unittest.TestCase):
    def test_deletion_events_are_denied_inside_artifact_root(self) -> None:
        inside = artifact_root() / "preserve-me"

        for event in ("os.remove", "os.rmdir", "os.unlink"):
            with self.subTest(event=event):
                with self.assertRaises(RuntimeError):
                    run_offline._audit_guard(event, (str(inside), -1))

    def test_move_events_are_denied_inside_artifact_root(self) -> None:
        source = artifact_root() / "source"
        destination = artifact_root() / "destination"

        for event in ("os.rename", "os.replace"):
            with self.subTest(event=event):
                with self.assertRaises(RuntimeError):
                    run_offline._audit_guard(
                        event,
                        (str(source), str(destination), -1, -1),
                    )

    def test_symlink_destination_escape_is_denied(self) -> None:
        inside_source = artifact_root() / "inside-source"
        outside_destination = run_offline.WORKTREE / "outside-link"

        with self.assertRaises(RuntimeError):
            run_offline._audit_guard(
                "os.symlink",
                (str(inside_source), str(outside_destination), -1),
            )

    def test_truncation_and_metadata_mutations_are_denied(self) -> None:
        inside = artifact_root() / "preserve-me"
        cases = (
            ("os.truncate", (str(inside), 0)),
            ("os.chmod", (str(inside), 0o600, -1)),
            ("os.utime", (str(inside), None, None, -1)),
        )

        for event, args in cases:
            with self.subTest(event=event):
                with self.assertRaises(RuntimeError):
                    run_offline._audit_guard(event, args)

    def test_create_and_read_inside_unique_artifact_folder_is_allowed(self) -> None:
        artifact_root = Path(os.environ["TEAKA_TEST_ARTIFACT_ROOT"])
        case_dir = artifact_root / f"guard-{uuid.uuid4().hex}"
        case_dir.mkdir(exist_ok=False)
        artifact = case_dir / "allowed.txt"

        artifact.write_text("preserved", encoding="utf-8")

        self.assertTrue(artifact.exists())
        self.assertEqual(artifact.read_text(encoding="utf-8"), "preserved")


if __name__ == "__main__":
    unittest.main()
