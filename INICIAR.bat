@echo off
rem ===================================================================
rem  Agente RRHH - arranque de un clic para entrega en otra laptop.
rem  Doble clic en este archivo y listo: prepara el entorno, siembra los
rem  datos ficticios y abre el chatbot (F4) y el dashboard (F3).
rem
rem  Para F1/F2 con IA real el responsable debe dejar su .env con las
rem  credenciales antes de entregar la carpeta (ver ENTREGA.md).
rem ===================================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"

set "VPY=.venv\Scripts\python.exe"
set "REQS=requirements-full.txt"

echo.
echo  ==========================================================
echo     AGENTE RRHH  -  entrega de un clic  (F1 F2 F3 F4)
echo  ==========================================================
echo.

REM ---------- 1) Python 3.12 o superior ----------
call :detectar_python
if defined LAUNCHER goto PY_OK

echo  [1/4] No se encontro Python 3.12 o superior en esta laptop.
echo.
where winget >nul 2>&1
if errorlevel 1 goto SIN_WINGET
echo  Instalando Python 3.12 con winget (puede tardar un minuto)...
winget install --exact --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "LAUNCHER=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "%ProgramFiles%\Python312\python.exe" set "LAUNCHER=%ProgramFiles%\Python312\python.exe"
if not defined LAUNCHER goto SIN_PYTHON

:PY_OK
echo  [1/4] Python listo: !LAUNCHER!

REM ---------- 2) Entorno virtual ----------
REM Se valida que el .venv funcione de verdad: si la carpeta se copio a otra
REM laptop, sus rutas absolutas quedan obsoletas y hay que rehacerlo.
"%VPY%" -c "import fastapi, streamlit, docx, pdfplumber" >nul 2>&1
if not errorlevel 1 goto VENV_OK
if exist ".venv" (
  echo  [2/4] El entorno virtual no es valido en este equipo; se rehace.
  rmdir /s /q ".venv"
)
echo  [2/4] Creando el entorno virtual .venv (solo la primera vez)...
!LAUNCHER! -m venv .venv
if errorlevel 1 goto FIN_ERROR
:VENV_OK
echo  [2/4] Entorno virtual listo.

REM ---------- 3) Dependencias ----------
"%VPY%" -c "import pathlib,sys;r=pathlib.Path('requirements-full.txt');s=pathlib.Path('.venv/.deps_ok');sys.exit(0 if s.exists() and s.stat().st_mtime>=r.stat().st_mtime else 1)" >nul 2>&1
if not errorlevel 1 goto DEPS_OK
echo  [3/4] Instalando dependencias (solo la primera vez, 1-3 min)...
"%VPY%" -m pip install --disable-pip-version-check --quiet --upgrade pip
"%VPY%" -m pip install --disable-pip-version-check --quiet -r "%REQS%"
if errorlevel 1 goto FIN_ERROR
"%VPY%" -c "import pathlib;pathlib.Path('.venv/.deps_ok').touch()"
:DEPS_OK
echo  [3/4] Dependencias listas.

REM ---------- 4) Sistema ----------
echo  [4/4] Iniciando el sistema...
echo.
"%VPY%" main.py demo %*
set "CODE=!errorlevel!"
echo.
if not "!CODE!"=="0" goto FIN_ERROR
echo  Sistema detenido correctamente.
pause
exit /b 0

REM ---------- Diagnosticos ----------
:SIN_WINGET
echo  Instala Python 3.12 desde https://www.python.org/downloads/
echo  (opcion "Add python.exe to PATH") y vuelve a hacer doble clic aqui.
goto FIN_ERROR

:SIN_PYTHON
echo  No se pudo preparar Python automaticamente.
goto FIN_ERROR

:FIN_ERROR
echo.
echo  ==========================================================
echo    NO SE PUDO ARRANCAR EL SISTEMA. Revisa el mensaje de arriba.
echo    Detalle tecnico en ENTREGA.md, seccion "Si algo falla".
echo  ==========================================================
pause
exit /b 1

REM ---------- Rutina: localizar un Python utilizable ----------
:detectar_python
set "LAUNCHER="
py -3.12 -c "import sys;raise SystemExit(0 if sys.version_info>=(3,12) else 1)" >nul 2>&1
if not errorlevel 1 set "LAUNCHER=py -3.12"
if defined LAUNCHER goto :eof
py -3 -c "import sys;raise SystemExit(0 if sys.version_info>=(3,12) else 1)" >nul 2>&1
if not errorlevel 1 set "LAUNCHER=py -3"
if defined LAUNCHER goto :eof
python -c "import sys;raise SystemExit(0 if sys.version_info>=(3,12) else 1)" >nul 2>&1
if not errorlevel 1 set "LAUNCHER=python"
if defined LAUNCHER goto :eof
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "LAUNCHER=%LocalAppData%\Programs\Python\Python312\python.exe"
if defined LAUNCHER goto :eof
if exist "%ProgramFiles%\Python312\python.exe" set "LAUNCHER=%ProgramFiles%\Python312\python.exe"
goto :eof
