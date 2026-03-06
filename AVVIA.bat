@echo off
title Qwen-Image-Layered
cd /d D:\AI\Qwen-Image-Layered
call venv\Scripts\activate
echo.
echo  Qwen-Image-Layered avviato!
echo  Apri il browser su: http://localhost:7869
echo.
python repo\src\app.py
pause