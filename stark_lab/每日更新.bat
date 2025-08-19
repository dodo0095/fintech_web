@echo off
call C:\ProgramData\Anaconda3\Scripts\activate py310

set "PATH=C:\py310;%PATH%"
set "PATH=C:\py310\Scripts;%PATH%"
python --version

cd C:\server website\fintech_web\stark_lab
call python update_new_version_20241028.py

pause