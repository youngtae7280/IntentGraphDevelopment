@echo off
setlocal
set "IGD_ROOT=%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONPYCACHEPREFIX=%TEMP%\IntentGraph\pycache"
set "DOTNET_CLI_HOME=%TEMP%\IntentGraph\dotnet-home"
set "NUGET_PACKAGES=%TEMP%\IntentGraph\nuget-packages"
set "NUGET_HTTP_CACHE_PATH=%TEMP%\IntentGraph\nuget-http-cache"

where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%IGD_ROOT%tools\igd.py" %*
exit /b %errorlevel%

:python_fallback
where python >nul 2>nul
if errorlevel 1 goto python_missing
python "%IGD_ROOT%tools\igd.py" %*
exit /b %errorlevel%

:python_missing
>&2 echo IntentGraph requires Python 3.11 or newer. Run "py -3 --version" or install Python, then retry.
exit /b 9009
