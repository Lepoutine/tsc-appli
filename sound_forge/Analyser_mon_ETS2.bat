@echo off
rem TSC Sound Forge - by Truck So Clean France : analyse de mon ETS2 (lecture seule, rien n'est modifie)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0analyse\Analyser_ETS2.ps1" %*
echo.
echo Rapport : %LOCALAPPDATA%\TruckSoCleanFrance\TSC\soundforge\rapport_analyse.md
pause
