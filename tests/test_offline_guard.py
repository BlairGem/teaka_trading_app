from __future__ import annotations

import os
import unittest
import uuid
import sys
import subprocess
from unittest.mock import patch
from pathlib import Path

from tests import run_offline


def artifact_root() -> Path:
    if run_offline.ARTIFACT_ROOT is None:
        raise RuntimeError("offline guard tests must run through tests/run_offline.py")
    return run_offline.ARTIFACT_ROOT


class OfflineGuardTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows metadata fallback')
    def test_wmi_failure_uses_native_version_without_command_and_restores_hook(self):
        import platform
        original = platform._syscmd_ver
        versions = []
        def numerical_import(name):
            if name == 'pandas':
                versions.append(platform.win32_ver()[1])
                with self.assertRaisesRegex(RuntimeError, 'blocked subprocess.Popen'):
                    subprocess.Popen([sys.executable, '-c', 'raise SystemExit(0)'])
        with patch.object(platform, '_wmi_query', side_effect=OSError('synthetic WMI unavailable')):
            run_offline._install_guard_then_import_numerics(add_guard=lambda _:None, import_module=numerical_import)
        native = sys.getwindowsversion()
        self.assertEqual(versions, ['.'.join(str(v) for v in (native.platform_version or native[:3]))])
        self.assertIs(platform._syscmd_ver, original)
        with self.assertRaisesRegex(ValueError, 'synthetic import failure'):
            run_offline._install_guard_then_import_numerics(add_guard=lambda _:None,
                import_module=lambda _: (_ for _ in ()).throw(ValueError('synthetic import failure')))
        self.assertIs(platform._syscmd_ver, original)

    def test_real_subprocess_and_devnull_write_remain_denied(self):
        with self.assertRaisesRegex(RuntimeError, 'blocked subprocess.Popen'):
            subprocess.Popen([sys.executable, '-c', 'raise SystemExit(0)'])
        with self.assertRaisesRegex(RuntimeError, 'blocked open outside'):
            os.open(os.devnull, os.O_RDWR)

    def test_numeric_bootstrap_installs_guard_before_imports(self) -> None:
        calls = []

        def import_module(name):
            calls.append(("import", name))
            if name == "pandas":
                run_offline._audit_guard("socket.gethostname", ())

        run_offline._install_guard_then_import_numerics(
            add_guard=lambda guard: calls.append(("guard", guard)),
            import_module=import_module,
        )

        self.assertEqual(calls[0], ("guard", run_offline._audit_guard))
        self.assertEqual(calls[1:], [("import", "numpy"), ("import", "pandas")])

    def test_socket_events_are_denied_outside_numeric_bootstrap(self) -> None:
        for event in (
            "socket.gethostname",
            "socket.__new__",
            "socket.connect",
            "socket.getaddrinfo",
        ):
            with self.subTest(event=event):
                with self.assertRaises(RuntimeError):
                    run_offline._audit_guard(event, ())

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
