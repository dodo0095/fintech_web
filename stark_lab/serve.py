"""Waitress 正式啟動腳本（供部署機使用）。

news.html 一載入會用 Promise.all 一次併發約 9 個 /api/news/* 請求。Waitress
預設只有 4 條工作執行緒，容納不下這波爆發，就會排隊並記 "Task queue depth"
警告。這裡把執行緒池調大（預設 12）以吸收初始爆發、消除該警告。

Caddy 反向代理目標為 127.0.0.1:8000（見專案 Caddyfile）。

啟動：
    cd stark_lab
    python serve.py

可用環境變數覆蓋預設值：
    STARKLAB_HOST     （預設 127.0.0.1）
    STARKLAB_PORT     （預設 8000）
    STARKLAB_THREADS  （預設 12）
"""
import os

from waitress import serve

from stark_lab.wsgi import application


def main():
    host = os.environ.get("STARKLAB_HOST", "127.0.0.1")
    port = int(os.environ.get("STARKLAB_PORT", "8000"))
    threads = int(os.environ.get("STARKLAB_THREADS", "12"))
    print("Starting waitress on {}:{} with {} threads".format(host, port, threads))
    serve(application, host=host, port=port, threads=threads)


if __name__ == "__main__":
    main()
