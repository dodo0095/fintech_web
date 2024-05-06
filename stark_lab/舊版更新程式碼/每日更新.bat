cd C:\Users\BANDAI\Anaconda3\Scripts
call activate.bat
call activate.bat C:\Users\BANDAI\Anaconda3\envs\myenv

cd C:\Users\BANDAI\Desktop\fintech_web\stark_lab
call python update_left.py
call python update_right.py
cd C:\Users\BANDAI\Desktop\fintech_web\stark_lab\crawler
call python  ptt_auto_news.py
pause