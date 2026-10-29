@echo off
rem Starts the local viewer server and opens the portfolio hub (viewers load their data from local files)
cd /d "%~dp0"
python serve_viewers.py
