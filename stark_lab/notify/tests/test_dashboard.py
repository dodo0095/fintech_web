"""Dashboard 測試 — 去 LINE 後只驗存取限制、隱藏標頭與基本渲染。"""
import pytest

from notify.models import PushLog

URL = "/_ops/notify-monitor/"


@pytest.mark.django_db
def test_localhost_can_access(client):
    resp = client.get(URL, REMOTE_ADDR="127.0.0.1")
    assert resp.status_code == 200
    assert "0050" in resp.content.decode()  # seed 標的


@pytest.mark.django_db
def test_ipv6_localhost_can_access(client):
    assert client.get(URL, REMOTE_ADDR="::1").status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("addr", ["10.0.0.5", "192.168.1.20", "203.0.113.9"])
def test_remote_address_forbidden(client, addr):
    assert client.get(URL, REMOTE_ADDR=addr).status_code == 403


@pytest.mark.django_db
def test_forwarded_header_cannot_bypass(client):
    """偽造 X-Forwarded-For 不得繞過本機限制（只認 REMOTE_ADDR）。"""
    resp = client.get(URL, REMOTE_ADDR="10.0.0.5", HTTP_X_FORWARDED_FOR="127.0.0.1")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_noindex_header_present(client):
    """隱藏層：回應須帶 X-Robots-Tag noindex，避免被搜尋引擎索引。"""
    resp = client.get(URL, REMOTE_ADDR="127.0.0.1")
    assert "noindex" in resp["X-Robots-Tag"]


@pytest.mark.django_db
def test_shows_recent_push_and_targets(client):
    PushLog.objects.create(
        channel="discord", market="tw", push_mode="dry_run", message="x",
        signal_count=3, status="success",
    )
    body = client.get(URL, REMOTE_ADDR="127.0.0.1").content.decode()
    assert "台股" in body      # 時段標籤
    assert "success" in body
    assert "0050" in body      # seed 標的
