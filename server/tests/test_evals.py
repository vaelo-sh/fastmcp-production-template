"""The eval harness: offline mode passes, and live mode parses both providers' replies
(against a local fake API, so no key or network is needed)."""

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_evals(*args, env=None):
    import os

    return subprocess.run(
        [sys.executable, "evals/run.py", *args, "--out", "evals/results/test.json"],
        cwd=ROOT, capture_output=True, text=True, env={**os.environ, **(env or {})},
    )


def test_offline_mode_passes():
    r = run_evals("--mode", "offline", env={"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": ""})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "accuracy=100%" in r.stdout


class FakeAPI(BaseHTTPRequestHandler):
    """Always 'calls' get_note(note_id='n-003'), in Anthropic or OpenAI format."""

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        assert body["tools"], "tools must be sent"
        if self.path == "/v1/messages":
            reply = {"content": [{"type": "tool_use", "name": "get_note", "input": {"note_id": "n-003"}}]}
        else:
            reply = {"choices": [{"message": {"tool_calls": [{"function": {"name": "get_note", "arguments": "{\"note_id\": \"n-003\"}"}}]}}]}
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def test_live_mode_against_fake_providers(tmp_path):
    srv = HTTPServer(("127.0.0.1", 0), FakeAPI)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    case = tmp_path / "one.yaml"
    case.write_text("cases:\n  - {id: open, prompt: open n-003, expected_tool: get_note, expected_args: {note_id: n-003}}\n"
                    "  - {id: find, prompt: find notes, expected_tool: search_notes}\n")
    try:
        for env in (
            {"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "", "EVAL_ANTHROPIC_BASE_URL": base},
            {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "x", "EVAL_OPENAI_BASE_URL": base},
        ):
            r = run_evals("--mode", "live", "--cases", str(case), "--min-accuracy", "0.5", env={"EVAL_MODEL": "fake-model", **env})
            assert r.returncode == 0, r.stdout + r.stderr
            assert "PASS  open" in r.stdout and "FAIL  find" in r.stdout and "args=ok" in r.stdout
    finally:
        srv.shutdown()
