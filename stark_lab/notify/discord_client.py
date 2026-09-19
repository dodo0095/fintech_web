"""Discord 推播 — Webhook + DRY_RUN（api-design §4）。

推播介面：push(text) -> PushResult。
Discord Webhook 免申請 Bot、免額度，POST content 即送到指定頻道。
"""
import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger("notify")

TIMEOUT = 10
# Discord 單則訊息 content 上限為 2000 字，超過需分段送出
CONTENT_LIMIT = 2000


@dataclass
class PushResult:
    status: str  # success / failed / dry_run / skipped
    mode: str    # webhook / dry_run / disabled
    error: str | None = None


def _split_chunks(text: str, limit: int = CONTENT_LIMIT) -> list[str]:
    """依行切分為多段，確保每段長度 <= limit（不破壞單行語意）。

    單行本身超過上限時才硬切。回傳至少一段（空字串輸入回傳 ['']）。
    """
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        # 單行過長：先沖掉暫存，再把長行硬切成數段
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    chunks.append(current)
    return chunks


def push(text: str) -> PushResult:
    """發送文字訊息到 Discord Webhook。

    - `DISCORD_ENABLED=false`：回傳 skipped，不呼叫 API。
    - `DRY_RUN=true`：只寫 log、不呼叫 API。
    - Webhook 未設定：回傳 failed。
    - 訊息超過 2000 字：自動分段逐則送出，任一段失敗即回 failed。
    """
    if not settings.DISCORD_ENABLED:
        return PushResult(status="skipped", mode="disabled")

    if settings.DRY_RUN:
        logger.info("[DRY_RUN] Discord 擬送訊息:\n%s", text)
        return PushResult(status="dry_run", mode="dry_run")

    url = settings.DISCORD_WEBHOOK_URL
    if not url:
        logger.error("Discord webhook 未設定（DISCORD_WEBHOOK_URL 為空）")
        return PushResult(status="failed", mode="webhook", error="missing webhook url")

    try:
        for chunk in _split_chunks(text):
            resp = requests.post(url, json={"content": chunk}, timeout=TIMEOUT)
            # Webhook 成功回 204 No Content；部分代理可能回 200
            if resp.status_code not in (200, 204):
                err = f"HTTP {resp.status_code}: {resp.text[:300]}"
                logger.error("Discord 推播失敗 %s", err)
                return PushResult(status="failed", mode="webhook", error=err)
    except requests.RequestException as e:
        logger.error("Discord 推播網路錯誤: %s", e)
        return PushResult(status="failed", mode="webhook", error=str(e))

    return PushResult(status="success", mode="webhook")
