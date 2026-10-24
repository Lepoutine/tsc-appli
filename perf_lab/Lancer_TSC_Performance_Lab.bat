@echo off
rem TSC Performance Lab - lance l'interface (Windows PowerShell, mode STA requis par WPF)
start "" powershell -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "%~dp0app\TSC_Performance_Lab.ps1"
