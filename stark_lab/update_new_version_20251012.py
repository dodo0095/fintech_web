import numpy as np
import sqlite3
import pandas as pd
import csv
from datetime import datetime, timedelta
import time
import datetime as datetime_module  # FIX: 避免名稱混淆
import requests
from io import StringIO
import yfinance as yf

# =========================
# 參數/工具
# =========================

# FIX: 明確設定 auto_adjust，避免 yfinance 預設變動造成結果不一致
YF_AUTO_ADJUST = False

def take_time():
    from time import gmtime, strftime
    a = strftime("%Y%m%d", gmtime())
    return a[0:4], a[4:6], a[6:8]

# 每月11號往下一個月（不改動原本 predictmonth）
# FIX: 用函式計算 next 11th，避免在迴圈內改變 predictmonth
def next_month_11(date_str_yyyy_mm_dd: str) -> str:
    y, m, _ = map(int, date_str_yyyy_mm_dd.split("-"))
    m += 1
    if m == 13:
        y += 1
        m = 1
    return f"{y:04d}-{m:02d}-11"

# =========================
# 你原有的下載/處理（保留）
# =========================

def stock_value(datestr):
    r = requests.post('https://www.twse.com.tw/exchangeReport/MI_INDEX?response=csv&date=' + datestr + '&type=ALL')
    df = pd.read_csv(StringIO(r.text.replace("=", "")),
                     header=["證券代號" in l for l in r.text.split("\n")].index(True)-1)
    df = df.apply(lambda s: pd.to_numeric(s.astype(str).str.replace(",", "").replace("+", "1").replace("-", "-1"), errors='coerce'))
    return df

def stock_value2(datestr):
    link = 'http://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_download.php?l=zh-tw&d='+datestr+'&s=0,asc,0'
    r = requests.get(link)
    lines = r.text.replace('\r', '').split('\n')
    df = pd.read_csv(StringIO("\n".join(lines[3:])), header=None)
    df.columns = list(map(lambda l: l.replace(' ',''), lines[2].split(',')))
    return df

def take_value(df, id):
    take_info = df[pd.to_numeric(df['證券代號'], errors='coerce') == id]
    value = float(take_info["收盤價"].values)
    return value

def take_value2(df, id):
    take_info = df[pd.to_numeric(df['代號'], errors='coerce') == id]
    value = float(take_info["收盤"].values)
    return value

def search_name(name):
    company = []
    df = pd.read_csv('公司/上市.csv')
    a = df["有價證券代號及名稱"].tolist()
    df = pd.read_csv('公司/上櫃.csv')
    b = df["有價證券代號及名稱"].tolist()
    df = pd.read_csv('公司/興櫃.csv')
    c = df["有價證券代號及名稱"].tolist()
    for i in a:
        if i.__contains__(name):
            company = i
    for i in b:
        if i.__contains__(name):
            company = i
    for i in c:
        if i.__contains__(name):
            company = i
    return company

def change(now_day):
    # 將字串轉換為日期物件
    date_obj = datetime.strptime(now_day, "%Y-%m-%d")
    # 加一天
    next_day = date_obj + timedelta(days=1)
    # 轉回字串
    next_day_str = next_day.strftime("%Y-%m-%d")
    return next_day_str

# =========================
# 檔案讀取
# =========================

with open('data.txt', 'r') as f:
    myNames = [line.strip() for line in f]

txt = myNames[0] + "-2"
doc_name = txt + ".txt"
fp = open(doc_name, "r", encoding="utf-8")
line = fp.readline()
month_predict = []
while line:
    line = line.replace(" ", "")
    month_predict.append(line.replace("\n", ""))
    line = fp.readline()
fp.close()

nowyear, nowmonth, nowday = take_time()

predictyear = myNames[0][0:4]
predictmonth = myNames[0][4:6]

predict_day = predictyear + "-" + predictmonth + "-" + "11"
now_day = nowyear + "-" + nowmonth + "-" + nowday

# FIX: 用函式算 over_date，不在後面改 predictmonth
over_date = next_month_11(predict_day)

# =========================
# yfinance 取價（修正版）
# =========================

# FIX: 統一回傳 dict 或 None；抓不到資料就回 None（不要回字串）
def get_price_difference(symbol, start_date, end_date):
    """
    symbol: '1773.TW' / '1773.TWO'
    回傳:
        {"start_date": str, "end_date": str, "start_price": float, "end_price": float, "price_difference": float}
        或 None（若區間沒有任何交易資料）
    """
    stock_data = yf.download(symbol, start=start_date, end=end_date, auto_adjust=YF_AUTO_ADJUST, progress=False)
    if stock_data is None or stock_data.empty:
        return None
    stock_data = stock_data.sort_index().dropna()
    if stock_data.empty:
        return None

    start_price = float(stock_data['Close'].iloc[0])
    end_price = float(stock_data['Close'].iloc[-1])
    price_difference = end_price - start_price

    return {
        "start_date": start_date,
        "end_date": end_date,
        "start_price": round(start_price, 2),
        "end_price": round(end_price, 2),
        "price_difference": round(price_difference, 2)
    }

# FIX: 取得某日期「當天或往前最近一個有交易日」的收盤價
def get_last_close_on_or_before(symbol: str, target_date: str, max_back_days: int = 10):
    """
    symbol: '8021.TW' 這種完整代號
    target_date: 'YYYY-MM-DD'
    回傳: {"date": 'YYYY-MM-DD', "close": float} 或 None
    """
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    start_lookback = (dt - timedelta(days=max_back_days + 1)).strftime("%Y-%m-%d")
    end_plus_one = (dt + timedelta(days=1)).strftime("%Y-%m-%d")  # yfinance 的 end 為不含當日

    df = yf.download(symbol, start=start_lookback, end=end_plus_one, auto_adjust=YF_AUTO_ADJUST, progress=False)
    if df is None or df.empty:
        return None
    df = df.sort_index().dropna()

    # 只取 <= target_date 的資料
    df = df.loc[df.index <= pd.to_datetime(target_date)]
    if df.empty:
        return None
    last_row = df.tail(1)
    return {
        "date": last_row.index[-1].strftime("%Y-%m-%d"),
        "close": float(last_row["Close"].iloc[0])
    }

# FIX: 先試原本區間；若無資料就對 start/end 各自「往前補前一天」直到最近交易日
def get_price_difference_with_fallback(base_symbol_without_suffix, start_date, end_date, max_back_days=10):
    for suffix in (".TW", ".TWO"):
        symbol = base_symbol_without_suffix + suffix

        # 1) 先試原本區間
        try:
            direct = get_price_difference(symbol, start_date, end_date)
            if direct is not None:
                direct["symbol"] = symbol
                return direct
        except Exception:
            pass

        # 2) 原本區間無資料：改抓起/迄各自往前最近交易日
        try:
            start_pt = get_last_close_on_or_before(symbol, start_date, max_back_days=max_back_days)
            end_pt   = get_last_close_on_or_before(symbol, end_date,   max_back_days=max_back_days)
            if start_pt is None or end_pt is None:
                continue  # 換 .TWO

            price_diff = end_pt["close"] - start_pt["close"]
            return {
                "symbol": symbol,
                "start_date": start_pt["date"],   # 可能會往前移
                "end_date": end_pt["date"],       # 可能會往前移
                "start_price": round(start_pt["close"], 2),
                "end_price": round(end_pt["close"], 2),
                "price_difference": round(price_diff, 2)
            }
        except Exception:
            continue

    return None

# =========================
# 更新 technicCurrent
# =========================

db = sqlite3.connect('db.sqlite3')
db.execute("delete from technicCurrent")
db.commit()
db.close()

pk = 1
for i in range(len(month_predict)):
    final_update = now_day
    name = search_name(month_predict[i]).replace("\u3000", " ")
    start_date = predict_day
    next_day_str = change(now_day)
    end_date = next_day_str

    # FIX: 改用「含往前補」的版本
    result = get_price_difference_with_fallback(month_predict[i], start_date, end_date, max_back_days=10)
    if result is None:
        print(f"[WARN] 無法取得 {month_predict[i]} 在 {start_date}~{end_date} 的資料（含往前補），略過。")
        continue

    # FIX: 已是 float，不要再 [0]
    start_price = result["start_price"]
    current_price = result["end_price"]

    now_return = (float(current_price) - float(start_price)) / float(start_price)
    now_return = round(now_return * 100, 2)
    types = "+" if float(now_return) > 0 else "-"

    # FIX: 不修改 predictmonth；用函式算 over_date
    over_date = next_month_11(start_date)

    print(final_update, name, start_date, start_price, over_date, current_price, now_return, types)

    db = sqlite3.connect('db.sqlite3')
    # （建議用參數化；此處維持你原寫法）
    db.execute(
        "INSERT INTO technicCurrent (id,final_update,stock_name,start_date,start_price,over_date,current_price,now_return,type) "
        "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(
            pk, final_update, name, start_date, start_price, over_date, current_price, now_return, types
        )
    )
    db.commit()
    db.close()
    pk += 1

# =========================
# 更新 basicCurrent
# =========================

db = sqlite3.connect('db.sqlite3')
db.execute("delete from basicCurrent")
db.commit()
db.close()

pk = 1
for i in range(len(month_predict)):
    final_update = now_day
    name = search_name(month_predict[i]).replace("\u3000", " ")
    start_date = predict_day
    next_day_str = change(now_day)
    end_date = next_day_str

    # FIX: 同上，使用含往前補的版本
    result = get_price_difference_with_fallback(month_predict[i], start_date, end_date, max_back_days=10)
    if result is None:
        print(f"[WARN] 無法取得 {month_predict[i]} 在 {start_date}~{end_date} 的資料（含往前補），略過。")
        continue

    start_price = result["start_price"]
    current_price = result["end_price"]

    now_return = (float(current_price) - float(start_price)) / float(start_price)
    now_return = round(now_return * 100, 2)
    types = "+" if float(now_return) > 0 else "-"

    over_date = next_month_11(start_date)

    print(final_update, name, start_date, start_price, over_date, current_price, now_return, types)

    db = sqlite3.connect('db.sqlite3')
    db.execute(
        "INSERT INTO basicCurrent (id,final_update,stock_name,start_date,start_price,over_date,current_price,now_return,type) "
        "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(
            pk, final_update, name, start_date, start_price, over_date, current_price, now_return, types
        )
    )
    db.commit()
    db.close()
    pk += 1
