@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem Запуск из исходников. При первом запуске ставит зависимости в .venv
if not exist ".venv\Scripts\python.exe" (
  set "PYEXE=python"
  where py >nul 2>nul && set "PYEXE=py -3"
  echo Первый запуск: создаю .venv и ставлю зависимости ...
  %PYEXE% -m venv .venv || goto :fail
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
)
start "" ".venv\Scripts\pythonw.exe" hyphen_gui.py %*
exit /b 0
:fail
echo Не удалось подготовить окружение. Нужен Python 3.10+ с https://www.python.org
pause
exit /b 1
