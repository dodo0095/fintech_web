"""訊息組裝（feature-spec §4）。

兩個區塊：
- `build_price_block`：價格區塊，**每個時點必推全部標的**（到點就推）。
- `build_message`：訊號區塊，只列有觸發的指標。
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from . import constants as C
from .indicators import Signal


@dataclass
class PriceRow:
    """單一標的的價格列；抓取失敗時 close/change_pct 為 None。"""

    display_name: str
    date: dt.date | None = None
    close: float | None = None
    change_pct: float | None = None
    note: str = ""


def build_price_block(rows: list[PriceRow]) -> str:
    """組裝價格區塊：每檔一行（收盤價＋漲跌幅＋日期）。無資料列仍會出現。

    日期逐檔顯示——台股與美股常非同一交易日，不能只放在標題。
    """
    if not rows:
        return ""
    lines = [C.PRICE_HEADER]
    for r in rows:
        if r.close is None:
            lines.append(f"・{r.display_name} —（{r.note or C.NOTE_NO_DATA}）")
            continue
        if r.change_pct is None or r.change_pct == 0:
            arrow = C.PRICE_FLAT
        elif r.change_pct > 0:
            arrow = C.PRICE_UP
        else:
            arrow = C.PRICE_DOWN
        pct = abs(r.change_pct or 0)
        line = f"・{r.display_name} {r.close:,.2f}（{arrow}{pct:.2f}%）{r.date:%m/%d}"
        if r.note:
            line += f"　{r.note}"
        lines.append(line)
    return "\n".join(lines)


def build_signal_summary(
    signaled: list[tuple[str, str]], no_signal_names: list[str]
) -> str:
    """組裝「今日訊號摘要」：一眼看出哪幾檔有／無訊號（feature-spec §4，長輩友善）。

    `signaled` 為 (顯示名, 方向標註) 序對，方向標註如「偏多／偏空／多空並存」。
    僅在本時點至少有一檔觸發時使用；全無觸發時改用 C.NO_SIGNAL_NOTE。
    """
    has_n, none_n = len(signaled), len(no_signal_names)
    lines = [f"{C.SUMMARY_TITLE}（{has_n} 檔有、{none_n} 檔無）"]
    if signaled:
        named = "、".join(f"{name}（{direction}）" for name, direction in signaled)
        lines.append(f"{C.SUMMARY_HAS}：{named}")
    if no_signal_names:
        lines.append(f"{C.SUMMARY_NONE}：" + "、".join(no_signal_names))
    return "\n".join(lines)


def build_message(display_name: str, trigger_date: dt.date, signals: list[Signal]) -> str:
    """組裝單一標的的通報訊息（依買進/賣出分組，含原因與建議）；無觸發回傳空字串。

    標題只留「標的＋日期」，醒目好認；免責標示集中於整體標題列與底部聲明，不逐檔重複。
    """
    if not signals:
        return ""
    lines = [f"📌 {display_name}　{trigger_date:%Y/%m/%d}"]

    groups = (
        ("🟢", "買進訊號", [s for s in signals if s.direction == C.BULLISH]),
        ("🔴", "賣出訊號", [s for s in signals if s.direction == C.BEARISH]),
    )
    for emoji, title, group in groups:
        if not group:
            continue
        lines.append("")
        lines.append(f"{emoji} {title}（{len(group)}）")
        for s in group:
            label = C.SIGNAL_LABEL.get((s.indicator, s.direction), f"{s.indicator} {s.direction}")
            plain = C.SIGNAL_PLAIN.get((s.indicator, s.direction), "")
            guide = C.SIGNAL_GUIDE.get((s.indicator, s.direction), {})
            # 白話當主標（長輩先看懂方向），專業名詞與數據退為附註。
            # 附註只留指標短名（label 冒號前段）＋實際數據，避免與白話描述重複。
            if plain:
                short = label.split("：", 1)[0]
                lines.append(f"・{C.PLAIN_EMOJI.get(s.direction, '')} {plain}")
                lines.append(f"　指標：{short}｜{s.detail}")
            else:
                lines.append(f"・{label}｜{s.detail}")
            if guide.get("advice"):
                lines.append(f"　建議：{guide['advice']}")

    # D. 衝突明示：同一標的本次同時有多、空新訊號時加註提醒（不取代上方買/賣分組顯示）。
    has_bull = any(s.direction == C.BULLISH for s in signals)
    has_bear = any(s.direction == C.BEARISH for s in signals)
    if has_bull and has_bear:
        lines.append("")
        lines.append(C.CONFLICT_NOTE)
    return "\n".join(lines)
