import datetime as dt

from notify import constants as C
from notify.indicators import Signal
from notify.messaging import (
    PriceRow,
    build_message,
    build_price_block,
    build_signal_summary,
)


def test_empty_signals_returns_empty_string():
    assert build_message("0050", dt.date(2026, 7, 26), []) == ""


# --- 價格區塊（到點必推）---
def _row(name="0050", close=101.45, pct=-0.25, note=""):
    return PriceRow(
        display_name=name, date=dt.date(2026, 7, 28), close=close, change_pct=pct, note=note
    )


def test_price_block_empty_rows_returns_empty_string():
    assert build_price_block([]) == ""


def test_price_block_shows_close_change_and_date():
    block = build_price_block([_row()])
    assert C.PRICE_HEADER in block
    assert "0050" in block
    assert "101.45" in block
    assert "0.25%" in block
    assert "07/28" in block


def test_price_block_direction_arrows():
    assert C.PRICE_DOWN in build_price_block([_row(pct=-0.25)])
    assert C.PRICE_UP in build_price_block([_row(pct=1.2)])
    assert C.PRICE_FLAT in build_price_block([_row(pct=0.0)])


def test_price_block_marks_stale_note():
    block = build_price_block([_row(note=C.NOTE_STALE)])
    assert C.NOTE_STALE in block


def test_price_block_handles_missing_data():
    block = build_price_block([PriceRow(display_name="黃金(GLD)", note=C.NOTE_NO_DATA)])
    assert "黃金(GLD)" in block
    assert C.NOTE_NO_DATA in block


def test_price_block_lists_every_row():
    rows = [_row(name=n) for n in ["0050", "S&P 500", "黃金(GLD)", "美元/日圓"]]
    block = build_price_block(rows)
    assert block.count("・") == 4


def test_message_lists_only_triggered():
    sigs = [
        Signal("ma", "bullish", "MA5 上穿 MA20"),
        Signal("macd", "bullish", "柱狀圖轉正"),
    ]
    msg = build_message("0050", dt.date(2026, 7, 26), sigs)
    assert "📌 0050" in msg
    assert "2026/07/26" in msg
    assert "🟢 買進訊號（2）" in msg
    assert "RSI" not in msg  # 未觸發不出現


def test_message_has_plain_indicator_and_advice():
    # 白話當主標、術語退為「指標：」附註；免責標示不逐檔重複
    sigs = [Signal("ma", "bullish", "MA5 上穿 MA20")]
    msg = build_message("0050", dt.date(2026, 7, 26), sigs)
    assert C.SIGNAL_PLAIN[("ma", "bullish")] in msg  # 白話總結
    assert "指標：" in msg  # 專業名詞保留為附註
    assert "建議：" in msg
    assert C.NON_ADVICE_TAG not in msg  # 標籤不逐檔重複


# --- 訊號摘要（長輩友善：一眼看出哪幾檔有／無訊號，含方向標註）---
def test_signal_summary_lists_has_with_direction_and_none():
    summary = build_signal_summary(
        [("S&P 500", "多空並存"), ("黃金(GLD)", "偏空")], ["0050", "美元/日圓"]
    )
    assert "2 檔有、2 檔無" in summary
    assert "🔔 有訊號：S&P 500（多空並存）、黃金(GLD)（偏空）" in summary
    assert "😴 無訊號：0050、美元/日圓" in summary


def test_signal_summary_omits_empty_none_line():
    summary = build_signal_summary([("0050", "偏多")], [])
    assert C.SUMMARY_HAS in summary
    assert C.SUMMARY_NONE not in summary


def test_message_groups_buy_and_sell_separately():
    sigs = [
        Signal("ma", "bullish", "金叉"),
        Signal("rsi", "bearish", "RSI=72"),
    ]
    msg = build_message("0050", dt.date(2026, 7, 26), sigs)
    assert "🟢 買進訊號（1）" in msg
    assert "🔴 賣出訊號（1）" in msg
    # 買進區塊在賣出區塊之前
    assert msg.index("買進訊號") < msg.index("賣出訊號")


# --- D. 衝突明示：同時多空 → 加註提醒，但仍保留買/賣分組 ---
def test_message_adds_conflict_note_when_both_directions():
    sigs = [
        Signal("rsi", "bullish", "RSI=28"),
        Signal("bollinger", "bearish", "觸及上軌"),
    ]
    msg = build_message("0050", dt.date(2026, 7, 26), sigs)
    assert C.CONFLICT_NOTE in msg
    # 加註不取代原本的買/賣分組顯示
    assert "🟢 買進訊號（1）" in msg
    assert "🔴 賣出訊號（1）" in msg


def test_message_no_conflict_note_when_single_direction():
    sigs = [
        Signal("ma", "bullish", "金叉"),
        Signal("macd", "bullish", "柱狀圖轉正"),
    ]
    msg = build_message("0050", dt.date(2026, 7, 26), sigs)
    assert C.CONFLICT_NOTE not in msg
