@echo off
rem Starts the local viewer server and opens this project's simulation viewer
cd /d "%~dp0.."
python serve_viewers.py BEng-CEA-Heatpump
