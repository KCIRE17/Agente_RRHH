@echo off
REM ============================================================
REM  _entorno.bat - Resuelve como ejecutar el proyecto.
REM  Uso:  call _entorno.bat
REM  Deja la variable RUN_CMD lista para usar:  %RUN_CMD% main.py
REM
REM  Prioridad:
REM    1) .venv\Scripts\python.exe  (entorno ya instalado)
REM    2) uv run python            (uv crea/sincroniza el entorno)
REM    3) python -m uv run python  (uv instalado via pip)
REM ============================================================
setlocal

set "RUN_CMD="

if exist ".venv\Scripts\python.exe" (
    set "RUN_CMD=.venv\Scripts\python.exe"
    goto :ok
)

where uv >NUL 2>&1
if not errorlevel 1 (
    set "RUN_CMD=uv run python"
    goto :ok
)

python -m uv --version >NUL 2>&1
if not errorlevel 1 (
    set "RUN_CMD=python -m uv run python"
    goto :ok
)

echo.
echo  [ERROR] No hay entorno instalado (ni .venv ni uv).
echo  Ejecuta INSTALAR.bat primero.
echo.
endlocal & exit /b 1

:ok
endlocal & set "RUN_CMD=%RUN_CMD%"
exit /b 0
