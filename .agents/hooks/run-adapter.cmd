@echo off
REM .agents/hooks/run-adapter.cmd
REM Windows wrapper routing execution into WSL bash. Uses the default WSL
REM distribution; set NANOPNP_WSL_DISTRO to name another one.
if defined NANOPNP_WSL_DISTRO (
    wsl.exe -d %NANOPNP_WSL_DISTRO% -e bash .agents/hooks/adapter.sh %*
) else (
    wsl.exe -e bash .agents/hooks/adapter.sh %*
)
