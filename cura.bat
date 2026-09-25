@echo off
rem Cura launcher.
rem   .\cura                 -> serve (best installed model stack)
rem   .\cura --light         -> serve --light (baselines only, fast startup)
rem   .\cura present          -> present (guided-tour demo mode)
rem   .\cura <subcommand> ... -> that subcommand (run, eval-stance, ...)
rem No first arg, or a leading flag, defaults to `serve`; a bare word is
rem treated as a subcommand and passed through unchanged.
setlocal
set "PY=%~dp0.venv\Scripts\python.exe"
set "FIRST=%~1"
if "%FIRST%"=="" (
  "%PY%" -m cura serve
) else if "%FIRST:~0,1%"=="-" (
  "%PY%" -m cura serve %*
) else (
  "%PY%" -m cura %*
)
