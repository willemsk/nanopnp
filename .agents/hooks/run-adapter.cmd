@echo off
REM .agents/hooks/run-adapter.cmd
REM Windows wrapper routing execution into WSL bash
wsl.exe -d Arch -e bash .agents/hooks/adapter.sh %*
