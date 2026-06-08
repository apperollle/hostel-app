@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Hostel App

echo.
echo  Hostel App — запуск сервера...
echo.

if not exist "venv\Scripts\python.exe" (
  echo  Создаю виртуальное окружение...
  python -m venv venv
  if errorlevel 1 (
    echo  ОШИБКА: установите Python с https://www.python.org/downloads/
    echo  При установке отметьте "Add python.exe to PATH"
    pause
    exit /b 1
  )
)

echo  Устанавливаю зависимости...
set PIP_NO_CACHE_DIR=1
set HTTP_PROXY=
set HTTPS_PROXY=
set ALL_PROXY=
venv\Scripts\python.exe -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo  Повторная установка без прокси...
  venv\Scripts\pip.exe install Flask Werkzeug
)

echo.
echo  ========================================
echo   Сайт откроется в браузере
echo   Адрес: http://127.0.0.1:5000
echo   Закройте это окно — сервер остановится
echo  ========================================
echo.

start "" "http://127.0.0.1:5000"
venv\Scripts\python.exe app.py

pause
