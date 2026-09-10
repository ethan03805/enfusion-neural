@echo off
py -3 "%~dp0scripts\play.py" %*
if errorlevel 1 pause
