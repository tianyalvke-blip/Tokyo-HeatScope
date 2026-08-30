@echo off
rem GLEN LST Agent - start the backend server (detached launcher)
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m uvicorn server.main:app --host 127.0.0.1 --port 8790
