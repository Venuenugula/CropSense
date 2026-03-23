import time

from utils import gemini


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeModels:
    def __init__(self, fn):
        self._fn = fn

    def generate_content(self, **kwargs):
        return self._fn(**kwargs)


class _FakeClient:
    def __init__(self, fn):
        self.models = _FakeModels(fn)


def test_call_gemini_timeout_returns_fallback(monkeypatch):
    def slow_call(**kwargs):
        time.sleep(0.05)
        return _FakeResponse("should-not-return")

    monkeypatch.setattr(gemini, "_client", _FakeClient(slow_call))
    result = gemini.call_gemini("test", retries=1, timeout_seconds=0.01)
    assert result == gemini.FALLBACK_RESPONSE


def test_call_gemini_retries_429_then_succeeds(monkeypatch):
    state = {"count": 0}

    def flaky_call(**kwargs):
        state["count"] += 1
        if state["count"] == 1:
            raise Exception("429 rate limit")
        return _FakeResponse("ok")

    monkeypatch.setattr(gemini, "_client", _FakeClient(flaky_call))
    monkeypatch.setattr(gemini.time, "sleep", lambda _: None)
    result = gemini.call_gemini("test", retries=2, timeout_seconds=1)
    assert result == "ok"
    assert state["count"] == 2
