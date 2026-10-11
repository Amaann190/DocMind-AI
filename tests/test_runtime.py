import io
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from utils.logs import setup_logger


class RuntimeTests(unittest.TestCase):
    def test_request_context_is_explicit_and_restored_after_nested_failure(self):
        from utils.runtime import st, request_state
        with self.assertRaises(RuntimeError):
            _ = st.session_state
        first = {"owner": "first"}
        with request_state(first):
            with self.assertRaises(ValueError):
                with request_state({"owner": "second"}):
                    self.assertEqual(st.session_state["owner"], "second")
                    raise ValueError("failed request")
            self.assertIs(st.session_state, first)
        with self.assertRaises(RuntimeError):
            _ = st.session_state

    def test_model_discovery_has_a_bounded_request_timeout(self):
        from utils.ollama import create_client

        client = create_client("http://127.0.0.1:11434")
        try:
            self.assertEqual(client._client.timeout.connect, 5.0)
            self.assertEqual(client._client.timeout.read, 5.0)
        finally:
            client._client.close()

    def test_logging_works_without_writable_files_and_does_not_duplicate(self):
        logger = logging.Logger("runtime-test")
        output = io.StringIO()
        with patch("utils.logs.logging.getLogger", return_value=logger), patch(
            "utils.logs.sys.stdout", output
        ), patch("utils.logs.logging.FileHandler", side_effect=PermissionError) as file:
            setup_logger().info("first message")
            setup_logger().info("second message")
        file.assert_not_called()
        self.assertEqual(output.getvalue().count("first message"), 1)
        self.assertEqual(output.getvalue().count("second message"), 1)
        self.assertFalse(logger.propagate)

    def test_unwritable_optional_log_keeps_console_available(self):
        logger = logging.Logger("runtime-test")
        output = io.StringIO()
        with patch("utils.logs.logging.getLogger", return_value=logger), patch(
            "utils.logs.sys.stdout", output
        ), patch("utils.logs.logging.FileHandler", side_effect=PermissionError):
            setup_logger("unwritable.log").info("still running")
        self.assertIn("stdout only", output.getvalue())
        self.assertIn("still running", output.getvalue())

    def test_endpoint_environment_and_blank_fallback(self):
        for value, expected in (
            (" http://host.docker.internal:11434 ", "http://host.docker.internal:11434"),
            ("   ", "http://localhost:11434"),
        ):
            with self.subTest(value=value):
                result = subprocess.run(
                    [sys.executable, "-c", "from backend.app import Settings; "
                     "print(Settings().endpoint)"],
                    cwd=Path(__file__).resolve().parents[1],
                    env={**os.environ, "DOCMIND_OLLAMA_ENDPOINT": value},
                    capture_output=True, text=True, timeout=30, check=True,
                )
                self.assertEqual(result.stdout.strip(), expected)

    @unittest.skipUnless(sys.platform == "win32", "Windows launcher")
    def test_launcher_uses_project_directory_and_does_not_take_occupied_port(self):
        source = Path(__file__).resolve().parents[1] / "run.ps1"
        with tempfile.TemporaryDirectory(prefix="docmind-launch-test-") as directory:
            root = Path(directory)
            (root / "run.ps1").write_text(source.read_text(), encoding="utf-8")
            (root / "frontend/dist").mkdir(parents=True)
            (root / "frontend/dist/index.html").write_text("Built React UI")
            (root / "python.ps1").write_text(
                "@{cwd=(Get-Location).Path; argv=$args} | ConvertTo-Json -Compress | "
                "Set-Content -LiteralPath $env:LAUNCH_RESULT\nexit 0", encoding="utf-8"
            )
            (root / "pipenv.ps1").write_text(
                "Write-Output (Join-Path $PSScriptRoot 'python.ps1')\nexit 0",
                encoding="utf-8",
            )
            harness = root / "check.ps1"
            harness.write_text(
                "function Get-Command { param($Name, $ErrorAction) "
                "[pscustomobject]@{Source=(Join-Path $env:LAUNCH_ROOT 'pipenv.ps1')} }\n"
                "function Get-NetTCPConnection { param($LocalPort, $State, $ErrorAction) "
                "if ($env:OCCUPIED -eq '1') { [pscustomobject]@{OwningProcess=42} } }\n"
                "& (Join-Path $env:LAUNCH_ROOT 'run.ps1') -Port 8766\n",
                encoding="utf-8",
            )
            result_file = root / "result.json"
            environment = {**os.environ, "LAUNCH_ROOT": directory,
                           "LAUNCH_RESULT": str(result_file), "OCCUPIED": "0"}
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness)],
                cwd=root.parent, env=environment, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            import json

            launched = json.loads(result_file.read_text(encoding="utf-8-sig"))
            self.assertEqual(Path(launched["cwd"]), root)
            self.assertIn("uvicorn", launched["argv"])
            self.assertIn("backend.app:app", launched["argv"])
            self.assertIn("8766", list(map(str, launched["argv"])))
            result_file.unlink()
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness)],
                cwd=root.parent, env={**environment, "OCCUPIED": "1"},
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already in use", result.stderr)
            self.assertFalse(result_file.exists())


if __name__ == "__main__":
    unittest.main()
