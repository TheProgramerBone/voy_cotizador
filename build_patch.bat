@echo off
REM ============================================================
REM  Genera el parche liviano de actualizacion (Output\QuoteTrip-Patch.zip)
REM  Solo app.py + quotetrip/ + assets/, sin reinstalar Python/Streamlit.
REM ============================================================
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo Usando interprete: %PY%
echo.

"%PY%" build_patch.py

echo.
pause
