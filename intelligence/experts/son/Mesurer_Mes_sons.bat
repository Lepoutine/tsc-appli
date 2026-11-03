@echo off
rem TSC Sound Engineering : mesure de tous les sons de Mes_sons (LECTURE SEULE, aucun son modifie).
rem Resultat : Bureau\TSC_Sound_Forge\mesures_mes_sons.csv (a ouvrir dans Excel)
set "ICI=%~dp0"
set "SONS=%USERPROFILE%\Desktop\TSC_Sound_Forge\Mes_sons"
if not exist "%SONS%" set "SONS=%USERPROFILE%\OneDrive\Bureau\TSC_Sound_Forge\Mes_sons"
python -I "%ICI%mesure_son.py" dossier "%SONS%" --csv "%SONS%\..\mesures_mes_sons.csv"
pause
