"""統一常數 — 指標參數與初始標的（api-design §3、feature-spec §1/§2）。

參數為業界標準值、統一套用於所有資產，非個別客製化。
"""

# --- 指標參數 ---
MA_FAST = 5
MA_SLOW = 20
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
KD_PERIOD = 9
KD_SMOOTH_K = 3
KD_SMOOTH_D = 3
KD_LOW = 20
KD_HIGH = 80
BB_PERIOD = 20
BB_STD = 2
# EMA 交叉（與 MA 交叉、MACD 相關性高，屬使用者指定新增）
EMA_FAST = 12
EMA_SLOW = 26
# 乖離率 BIAS：(收盤−MA_N)/MA_N×100；門檻為統一預設值，可視真實觸發頻率調整
BIAS_PERIOD = 10
BIAS_OVERSOLD = -5.0
BIAS_OVERBOUGHT = 5.0
# 寶塔線 TOWER：僅收盤價、翻紅/翻黑，參考前 N 根收盤
TOWER_REF = 2

# --- ADX 盤整過濾（whipsaw 假訊號抑制）---
# ADX(14) Wilder 標準算法；ADX < ADX_RANGING_THRESHOLD 視為盤整（無趨勢）。
ADX_PERIOD = 14
ADX_RANGING_THRESHOLD = 25
# 交叉/趨勢型指標：盤整時易來回假訊號（前日買、隔日賣），盤整期間壓制之。
TREND_INDICATORS = {"ma", "ema", "macd", "kd", "tower"}
# 其餘為均值回歸型（rsi, bias, bollinger），盤整時仍具參考價值、不壓制。

# 抓取後至少需要的資料筆數（暖機期，feature-spec §3.1）
MIN_ROWS = 60

# 交易日新鮮度容忍天數（跨週末/假日），超過視為今日未開盤/資料過舊
FRESHNESS_TOLERANCE_DAYS = 4

# --- 指標與方向代碼 ---
INDICATORS = ("ma", "macd", "rsi", "kd", "bollinger", "ema", "bias", "tower")
BULLISH = "bullish"
BEARISH = "bearish"

# 訊息 emoji 對映（feature-spec §4）
DIRECTION_EMOJI = {BULLISH: "🟢", BEARISH: "🔴"}

# 觸發文案
SIGNAL_LABEL = {
    ("ma", BULLISH): "MA黃金交叉：MA5 上穿 MA20",
    ("ma", BEARISH): "MA死亡交叉：MA5 下穿 MA20",
    ("macd", BULLISH): "MACD轉多：柱狀圖轉正",
    ("macd", BEARISH): "MACD轉空：柱狀圖轉負",
    ("rsi", BULLISH): "RSI超賣（<30）",
    ("rsi", BEARISH): "RSI超買（>70）",
    ("kd", BULLISH): "KD低檔黃金交叉",
    ("kd", BEARISH): "KD高檔死亡交叉",
    ("bollinger", BULLISH): "布林下軌：收盤觸及/跌破下軌",
    ("bollinger", BEARISH): "布林上軌：收盤觸及/突破上軌",
    ("ema", BULLISH): "EMA黃金交叉：EMA12 上穿 EMA26",
    ("ema", BEARISH): "EMA死亡交叉：EMA12 下穿 EMA26",
    ("bias", BULLISH): "乖離率超賣（BIAS(10)≤-5%）",
    ("bias", BEARISH): "乖離率超買（BIAS(10)≥+5%）",
    ("tower", BULLISH): "寶塔線翻紅（轉多）",
    ("tower", BEARISH): "寶塔線翻黑（轉空）",
}

# 免責標籤（標題列）與底部聲明（feature-spec §4）——推播建議屬敏感內容，一律標示非投資建議
NON_ADVICE_TAG = "[非投資建議]"
DISCLAIMER = "⚠️ 本通知為技術指標的機械式提示，非投資建議，請自行評估風險。"
# 當本時點全部標的皆無觸發訊號時附上的說明（避免收訊者誤以為系統出錯）
NO_SIGNAL_NOTE = "✅ 今日無指標訊號（僅列收盤價）"
# 有訊號時的「訊號摘要」區塊——讓長輩使用者一眼看出哪幾檔有／無訊號
SUMMARY_TITLE = "🔎 今日訊號摘要"
SUMMARY_HAS = "🔔 有訊號"
SUMMARY_NONE = "😴 無訊號"
# 摘要中每檔的方向標註（依該檔觸發的買進/賣出組合判定）
SUMMARY_DIR = {"bull": "偏多", "bear": "偏空", "mixed": "多空並存"}
# 同一標的同時出現多、空新訊號時的加註提醒（D 衝突明示；不取代買/賣分組顯示）
CONFLICT_NOTE = "⚠️ 盤整訊號分歧，建議觀望"

# 每條訊號的「白話總結」——保留專業名詞，另加一句人話讓長輩看得懂方向
PLAIN_EMOJI = {BULLISH: "📈", BEARISH: "📉"}
SIGNAL_PLAIN = {
    ("ma", BULLISH): "均線翻多、短線走強",
    ("ma", BEARISH): "均線翻空、短線走弱",
    ("macd", BULLISH): "動能翻多、買氣轉強",
    ("macd", BEARISH): "動能翻空、賣壓轉強",
    ("rsi", BULLISH): "跌深、有反彈機會",
    ("rsi", BEARISH): "漲多、容易回檔",
    ("kd", BULLISH): "低檔轉強、有落底反彈跡象",
    ("kd", BEARISH): "高檔轉弱、有見頂回落跡象",
    ("bollinger", BULLISH): "跌到相對低點、統計上偏極端",
    ("bollinger", BEARISH): "漲到相對高點、統計上偏極端",
    ("ema", BULLISH): "均線翻多、趨勢偏強",
    ("ema", BEARISH): "均線翻空、趨勢偏弱",
    ("bias", BULLISH): "短線跌深、乖離過大",
    ("bias", BEARISH): "短線漲多、乖離過大",
    ("tower", BULLISH): "股價由黑翻紅、短線偏多",
    ("tower", BEARISH): "股價由紅翻黑、短線偏空",
}

# 底部總說明：交代「有 8 項指標，只推達標者」，讓沒出現的指標＝未達門檻而非漏掉
THRESHOLD_NOTE = (
    "ℹ️ 本系統每日檢查 8 項指標（MA、MACD、RSI、KD、布林、EMA、乖離、寶塔線），\n"
    "　只列「達到門檻」的訊號；未出現的指標＝目前中性、未達推送標準。"
)

# --- 價格區塊（feature-spec §4）：每個時點必推全部標的收盤價 ---
PRICE_HEADER = "💹 最新收盤價"
# 漲/跌/平 的方向符號
PRICE_UP = "▲"
PRICE_DOWN = "▼"
PRICE_FLAT = "－"
# 價格列的附註
NOTE_STALE = "休市"
NOTE_NO_DATA = "資料暫時無法取得"

# 推播訊息標題（中性）——每個時點都推全部標的，故不綁單一市場
DAILY_TITLE = "每日盤勢通報"
# 時段標題（market → 顯示名），僅供本機 Dashboard 區分時段用（非推播內容）
MARKET_LABEL = {"tw": "台股時段", "us": "美股時段"}

# 每個訊號的「原因 / 建議」文案，用中性字眼（參考/留意/可考慮），不用指示性字眼
SIGNAL_GUIDE = {
    ("ma", BULLISH): {"reason": "短期均線由下往上穿越長期均線，短線動能轉強、趨勢偏多。",
                      "advice": "偏多參考；避免追高，可等回測均線、量能配合再進場。"},
    ("ma", BEARISH): {"reason": "短期均線跌破長期均線，短線動能轉弱、趨勢偏空。",
                      "advice": "偏空/減碼參考；反彈至均線附近留意壓力。"},
    ("macd", BULLISH): {"reason": "快線上穿訊號線、柱狀圖翻正，動能由空轉多。",
                        "advice": "偏多參考；搭配均線方向與量能確認較穩。"},
    ("macd", BEARISH): {"reason": "快線跌破訊號線、柱狀圖翻負，動能轉弱。",
                        "advice": "偏空/減碼參考；留意是否進入盤整。"},
    ("rsi", BULLISH): {"reason": "短線跌深進入超賣區，出現反彈機會。",
                       "advice": "偏多（搶反彈）參考，非保證反轉；宜等止跌訊號再進場。"},
    ("rsi", BEARISH): {"reason": "短線漲多進入超買區，回檔機率升高。",
                       "advice": "偏空/減碼參考；勿追高，留意轉弱K線。"},
    ("kd", BULLISH): {"reason": "KD 在低檔(<20)黃金交叉，短線由弱轉強、有落底反彈跡象。",
                      "advice": "偏多參考；留意反彈力道與是否低檔鈍化。"},
    ("kd", BEARISH): {"reason": "KD 在高檔(>80)死亡交叉，短線由強轉弱、有見頂回落跡象。",
                      "advice": "偏空/減碼參考；留意高檔鈍化。"},
    ("bollinger", BULLISH): {"reason": "收盤觸及/跌破下軌，相對均值偏低、統計上偏極端。",
                             "advice": "偏多（均值回歸）參考；若沿下軌下行代表強空，需搭配趨勢判斷。"},
    ("bollinger", BEARISH): {"reason": "收盤觸及/突破上軌，相對均值偏高。",
                             "advice": "偏空（回歸）參考；強多時可能沿上軌續攻，勿單看此訊號。"},
    ("ema", BULLISH): {"reason": "較敏感的指數均線黃金交叉，中短期趨勢偏多。",
                       "advice": "偏多參考；與 MA/MACD 同向時訊號更一致。"},
    ("ema", BEARISH): {"reason": "指數均線死亡交叉，中短期趨勢轉弱。",
                       "advice": "偏空/減碼參考。"},
    ("bias", BULLISH): {"reason": "收盤大幅低於均線、短線跌深，乖離過大。",
                        "advice": "偏多（乖離修正）參考；強勢下跌時乖離可能持續擴大，非立即反轉。"},
    ("bias", BEARISH): {"reason": "收盤大幅高於均線、短線漲多，乖離過大。",
                        "advice": "偏空/減碼參考；勿追高。"},
    ("tower", BULLISH): {"reason": "寶塔線由黑翻紅、收盤突破前波高點，趨勢由空轉多。",
                         "advice": "偏多參考；翻紅初期較有意義，留意假突破。"},
    ("tower", BEARISH): {"reason": "寶塔線由紅翻黑、收盤跌破前波低點，趨勢由多轉空。",
                         "advice": "偏空/減碼參考；留意假跌破。"},
}

# --- 初始追蹤標的（feature-spec §1）---
DEFAULT_TARGETS = [
    {"symbol": "0050.TW", "display_name": "0050", "asset_class": "tw_stock", "market": "tw"},
    {"symbol": "^GSPC", "display_name": "S&P 500", "asset_class": "us_index", "market": "us"},
    {"symbol": "GLD", "display_name": "黃金(GLD)", "asset_class": "gold", "market": "us"},
    {"symbol": "USDJPY=X", "display_name": "美元/日圓", "asset_class": "forex", "market": "us"},
]
