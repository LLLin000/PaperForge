@echo off
REM Open Design daemon launcher — project-local install
set "OD_SOURCE=%~dp0source"
node "%OD_SOURCE%\apps\daemon\dist\cli.js" --port 17456 --no-open %*
