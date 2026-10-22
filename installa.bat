@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython
%PY% installa_traduzione.py %*
goto fine
:nopython
echo Python non risulta installato.
echo Scaricalo da https://www.python.org/downloads/ e durante l'installazione
echo spunta "Add python.exe to PATH". Poi riapri questo file.
:fine
echo.
pause
