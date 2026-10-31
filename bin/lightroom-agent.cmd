@echo off
rem Lightroom Agent launcher (Windows). Keeps a private Python environment in %USERPROFILE%\.lightroom-agent\venv.
rem After changing requirements.txt delete that venv folder to rebuild it.
setlocal
set "ROOT=%~dp0.."
if "%LIGHTROOM_AGENT_HOME%"=="" set "LIGHTROOM_AGENT_HOME=%USERPROFILE%\.lightroom-agent"
set "VENV=%LIGHTROOM_AGENT_HOME%\venv"
if not exist "%VENV%\Scripts\python.exe" (
  echo lightroom-agent: setting up Python environment in %VENV% ^(first run, 1-3 minutes^)... 1>&2
  py -3 -m venv "%VENV%" 1>&2 || python -m venv "%VENV%" 1>&2 || exit /b 1
  "%VENV%\Scripts\python.exe" -m pip install -q --upgrade pip 1>&2
  "%VENV%\Scripts\python.exe" -m pip install -q -r "%ROOT%\requirements.txt" 1>&2 || exit /b 1
)
"%VENV%\Scripts\python.exe" -I "%ROOT%\pipeline\cli.py" %*
