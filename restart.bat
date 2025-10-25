@echo off
cls
echo ⏳ Restarting Mochi Bot...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 >nul
start cmd /k "cd /d D:\!RhebitWork\!Project\Active Project\!ProgramLearning\Discord Bot\mochi && python main.py"