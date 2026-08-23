@echo off
REM ============================================================
REM  Construye VoyCotizador.exe (carpeta unica) con PyInstaller.
REM  Usa el Python del .venv si existe e instala las dependencias
REM  de escritorio (PyInstaller, pywebview) si hacen falta.
REM ============================================================
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo Usando interprete: %PY%
echo.

REM --- Asegurar dependencias de escritorio ---
"%PY%" -c "import PyInstaller" 2>NUL
if errorlevel 1 (
  echo Falta PyInstaller. Instalando dependencias de escritorio...
  "%PY%" -m pip install -r requirements-desktop.txt
  echo.
)

REM --- Compilar ---
"%PY%" -m PyInstaller --noconfirm --clean VoyCotizador.spec

echo.
if exist "dist\VoyCotizador\VoyCotizador.exe" (
  echo ============================================================
  echo  LISTO. El programa quedo en:
  echo    dist\VoyCotizador\VoyCotizador.exe
  echo  Reparte TODA la carpeta  dist\VoyCotizador\
  echo ============================================================
) else (
  echo ============================================================
  echo  ERROR: no se genero el ejecutable.
  echo  Revisa los mensajes de arriba para ver la causa.
  echo ============================================================
)
pause