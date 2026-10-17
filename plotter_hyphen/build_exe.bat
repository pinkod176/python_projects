@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
echo === Сборка PlotterHyphen.exe ===

rem --- найти Python 3.10+ (сначала python из PATH, потом py-лаунчер)
set "PYEXE="
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PYEXE=python"
if not defined PYEXE (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PYEXE=py -3"
)
if not defined PYEXE (
  echo Не найден Python 3.10 или новее. Установите его с https://www.python.org
  echo ^(при установке отметьте "Add python.exe to PATH"^) и запустите build_exe.bat снова.
  goto :fail
)
%PYEXE% --version

rem --- виртуальное окружение и зависимости
if not exist ".venv\Scripts\python.exe" (
  echo Создаю виртуальное окружение .venv ...
  %PYEXE% -m venv .venv || goto :fail
)
set "VPY=.venv\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip || goto :fail
"%VPY%" -m pip install -r requirements.txt -r requirements-build.txt || goto :fail

rem --- тесты (пропустить: build_exe.bat notest)
if /i not "%~1"=="notest" (
  set "QT_QPA_PLATFORM=offscreen"
  "%VPY%" -m pytest -q tests || (echo Тесты не прошли. & goto :fail)
  set "QT_QPA_PLATFORM="
)

rem --- сборка одного exe
"%VPY%" -m PyInstaller --noconfirm --clean PlotterHyphen.spec || goto :fail

rem --- самопроверка собранного exe
if exist "build\selftest" rmdir /s /q "build\selftest"
start "" /wait "dist\PlotterHyphen.exe" --selftest "build\selftest"
if errorlevel 1 (
  echo Самопроверка exe НЕ прошла:
  type "build\selftest\selftest.txt"
  goto :fail
)
type "build\selftest\selftest.txt"
for %%F in ("dist\PlotterHyphen.exe") do echo Готово: %%~fF  (%%~zF байт)
if /i not "%~1"=="ci" if /i not "%~2"=="ci" pause
exit /b 0

:fail
echo.
echo *** ОШИБКА СБОРКИ ***
if /i not "%~1"=="ci" if /i not "%~2"=="ci" pause
exit /b 1
