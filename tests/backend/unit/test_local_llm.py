"""Real HTTP/CrewAI integration against a test-only OpenAI-compatible server."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from core.llm_provider import check_model_server


@pytest.fixture
def model_server():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            calls.append((self.path, None))
            body = json.dumps({"data": [{"id": "local-test-model"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append((self.path, payload))
            message = {"role": "assistant", "content": "OK नमस्ते"}
            finish = "stop"
            if payload.get("tools"):
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "probe-1",
                            "type": "function",
                            "function": {"name": "agis_probe", "arguments": "{}"},
                        }
                    ],
                }
                finish = "tool_calls"
            elif "single boolean field" in str(payload.get("messages")):
                message["content"] = '{"ok": true}'
            body = json.dumps(
                {
                    "id": "test-response",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "local-test-model",
                    "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_local_model_check_is_read_only_and_exact(model_server):
    url, calls = model_server
    check_model_server(url, "openai/local-test-model", "lm-studio")
    with pytest.raises(RuntimeError, match="not offered"):
        check_model_server(url, "openai/missing-model", "lm-studio")
    assert calls == [("/v1/models", None), ("/v1/models", None)]


def test_crewai_reaches_local_chat_endpoint_without_cloud_fallback(model_server):
    from crewai import LLM

    url, calls = model_server
    llm = LLM(
        model="openai/local-test-model",
        base_url=url,
        api_key="lm-studio",
        timeout=10,
        max_tokens=32,
    )
    assert llm.call("Reply OK") == "OK नमस्ते"
    assert calls[-1][0] == "/v1/chat/completions"
    assert calls[-1][1]["model"] == "local-test-model"


def test_unreachable_local_server_never_selects_a_substitute():
    def offline(_):
        raise httpx.ConnectError("offline")

    with httpx.Client(transport=httpx.MockTransport(offline)) as client:
        with pytest.raises(RuntimeError, match="unavailable"):
            check_model_server("http://127.0.0.1:1234/v1", "openai/local-test-model", client=client)


def test_local_generation_probe_checks_json_and_tool_execution(model_server):
    from core.llm_provider import probe_local_generation

    url, calls = model_server
    probe_local_generation(url, "openai/local-test-model", "lm-studio")
    assert any(payload and payload.get("tools") for _, payload in calls)
    assert all(path == "/v1/chat/completions" for path, _ in calls)
