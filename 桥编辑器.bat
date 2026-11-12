@echo off
rem ASCII-only launcher: batch files are read in the OEM codepage,
rem so any non-ASCII character in here becomes garbage. We therefore
rem find the .pyw by wildcard at runtime instead of naming it.
cd /d "%~dp0"
for %%F in (*.pyw) do (
    start "" pythonw "%%~fF" %*
    exit /b 0
)
echo [error] no .pyw launcher found next to this bat
pause