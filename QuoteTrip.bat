@echo off
REM ============================================================
REM  Inicia QuoteTrip en una ventana de escritorio.
REM  Usa el Python que esta en la subcarpeta  python\  (portable),
REM  por lo que NO requiere Python instalado en el sistema.
REM ============================================================
cd /d "%~dp0"
start "" "%~dp0python\python.exe" "%~dp0desktop.py"
