"""Discord 推播分支測試 — 一律 mock requests.post，不真的呼叫 Webhook。"""
import pytest
import requests

from notify import discord_client


class _FakeResp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


def _recorder(resp):
    """回傳 (fake_post, calls)；記錄每次呼叫並回傳指定 resp。"""
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append({"url": url, "json": json})
        return resp

    return fake_post, calls


def test_disabled_returns_skipped_without_call(monkeypatch, settings):
    settings.DISCORD_ENABLED = False

    def _boom(*a, **k):
        raise AssertionError("頻道關閉不應呼叫 API")

    monkeypatch.setattr(discord_client.requests, "post", _boom)
    result = discord_client.push("hello")
    assert result.status == "skipped"
    assert result.mode == "disabled"


def test_dry_run_does_not_call_api(monkeypatch, settings):
    settings.DISCORD_ENABLED = True
    settings.DRY_RUN = True

    def _boom(*a, **k):
        raise AssertionError("DRY_RUN 不應呼叫 requests.post")

    monkeypatch.setattr(discord_client.requests, "post", _boom)
    result = discord_client.push("hello")
    assert result.status == "dry_run"
    assert result.mode == "dry_run"


def test_webhook_success_204(monkeypatch, settings):
    settings.DISCORD_ENABLED = True
    settings.DRY_RUN = False
    settings.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/x/y"
    fake_post, calls = _recorder(_FakeResp(204))
    monkeypatch.setattr(discord_client.requests, "post", fake_post)

    result = discord_client.push("hello")
    assert result.status == "success"
    assert result.mode == "webhook"
    assert calls[0]["url"] == settings.DISCORD_WEBHOOK_URL
    assert calls[0]["json"] == {"content": "hello"}


def test_missing_webhook_is_failed_without_call(monkeypatch, settings):
    settings.DISCORD_ENABLED = True
    settings.DRY_RUN = False
    settings.DISCORD_WEBHOOK_URL = ""

    def _boom(*a, **k):
        raise AssertionError("缺 webhook 不應呼叫 API")

    monkeypatch.setattr(discord_client.requests, "post", _boom)
    result = discord_client.push("hello")
    assert result.status == "failed"
    assert result.error == "missing webhook url"


def test_non_2xx_is_failed(monkeypatch, settings):
    settings.DISCORD_ENABLED = True
    settings.DRY_RUN = False
    settings.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/x/y"
    fake_post, _ = _recorder(_FakeResp(429, "rate limited"))
    monkeypatch.setattr(discord_client.requests, "post", fake_post)

    result = discord_client.push("hello")
    assert result.status == "failed"
    assert "HTTP 429" in result.error


def test_request_exception_is_failed_not_raised(monkeypatch, settings):
    settings.DISCORD_ENABLED = True
    settings.DRY_RUN = False
    settings.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/x/y"

    def _raise(*a, **k):
        raise requests.RequestException("network down")

    monkeypatch.setattr(discord_client.requests, "post", _raise)
    result = discord_client.push("hello")  # 不應拋出
    assert result.status == "failed"
    assert "network down" in result.error


def test_long_message_split_into_chunks(monkeypatch, settings):
    """超過 2000 字自動分段，逐段送出，每段皆 <= 上限。"""
    settings.DISCORD_ENABLED = True
    settings.DRY_RUN = False
    settings.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/x/y"
    fake_post, calls = _recorder(_FakeResp(204))
    monkeypatch.setattr(discord_client.requests, "post", fake_post)

    # 每行 100 字、共 60 行 → 約 6060 字，須切成多段
    text = "\n".join(["x" * 100 for _ in range(60)])
    result = discord_client.push(text)

    assert result.status == "success"
    assert len(calls) > 1
    assert all(len(c["json"]["content"]) <= discord_client.CONTENT_LIMIT for c in calls)


def test_split_chunks_hard_splits_overlong_line():
    """單行超過上限時硬切。"""
    chunks = discord_client._split_chunks("a" * 5000, limit=2000)
    assert all(len(c) <= 2000 for c in chunks)
    assert "".join(chunks) == "a" * 5000
